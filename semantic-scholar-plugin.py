from fastmcp import FastMCP
import httpx
from typing import Optional
from pydantic import Field

# Create the MCP server with configuration
mcp = FastMCP(
    "Semantic Scholar Search 📚",
    dependencies=["httpx", "pydantic"]
)

# Constants
FIELDS = ','.join(['title', 'year', 'authors', 'venue', 'citationCount', 'externalIds', 'abstract', 'url'])
BASE_URL = 'https://api.semanticscholar.org/graph/v1/paper/search'

@mcp.tool()
async def search_papers_via_semanticscholar(
    keyword: str = Field(..., description="Search query for academic papers (e.g., 'quantum computing')"),
    limit: int = Field(10, description="Maximum number of results to return", ge=1, le=25),
    year_from: Optional[int] = Field(None, description="Filter papers from this year onwards"),
    year_to: Optional[int] = Field(None, description="Filter papers up to this year")
) -> str:
    """
    Search for academic papers and research articles across multiple disciplines using Semantic Scholar's database.
    Returns formatted results with titles, authors, abstracts, and citations.
    """
    # Build the query
    query_params = {
        'query': keyword,
        'limit': limit,
        'fields': FIELDS
    }
    
    if year_from or year_to:
        year_filter = ""
        if year_from and year_to:
            year_filter = f"{year_from}-{year_to}"
        elif year_from:
            year_filter = f"{year_from}-"
        elif year_to:
            year_filter = f"-{year_to}"
        query_params['year'] = year_filter

    # Make the request
    async with httpx.AsyncClient() as client:
        params = {
            'query': keyword,
            'limit': str(limit),
            'fields': FIELDS
        }
        if year_from or year_to:
            year_filter = ""
            if year_from and year_to:
                year_filter = f"{year_from}-{year_to}"
            elif year_from:
                year_filter = f"{year_from}-"
            elif year_to:
                year_filter = f"-{year_to}"
            params['year'] = year_filter
            
        response = await client.get(BASE_URL, params=params)
        data = response.json()

    if not data.get('data'):
        return "No papers found matching your search criteria."

    # Format the results
    markdown = f"## Academic Search Results\n"
    markdown += f"📚 Found {data['total']:,} papers. Showing {len(data['data'])} recent results:\n\n"

    for index, paper in enumerate(data['data'], 1):
        # Title with year
        markdown += f"### {index}. {paper['title']} ({paper.get('year', 'N/A')})\n\n"

        # Publication and impact
        markdown += f"📍 **Publication:** {paper.get('venue', 'N/A')}\n"
        citations = paper.get('citationCount', 0)
        markdown += f"📊 **Impact:** {citations} citation{'s' if citations != 1 else ''}\n"

        # Authors
        if paper.get('authors'):
            markdown += "👥 **Research Team:** "
            authors = paper['authors'][:3]
            author_names = []
            for author in authors:
                name_parts = author['name'].split()
                last_name = name_parts[-1]
                initials = '.'.join(part[0] for part in name_parts[:-1])
                author_names.append(f"{last_name}, {initials}." if initials else last_name)
            
            markdown += ', '.join(author_names)
            if len(paper['authors']) > 3:
                markdown += ' et al.'
            markdown += '\n'

        # DOI
        if paper.get('externalIds', {}).get('DOI'):
            doi = paper['externalIds']['DOI']
            markdown += f"🔗 **DOI:** [{doi}](https://doi.org/{doi})\n"

        # Abstract
        if paper.get('abstract'):
            markdown += f"📝 **Abstract:** {paper['abstract']}\n"

        # URL
        if paper.get('url'):
            markdown += f"🌐 **URL:** [Link]({paper['url']})\n"

        markdown += "\n---\n\n"

    return markdown