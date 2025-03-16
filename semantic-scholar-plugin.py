from mcp.server.fastmcp import FastMCP
import httpx
from typing import Optional
import os
from pydantic import Field
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("semantic-scholar-mcp")

# Get API key from environment variable
API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")

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
    # Build the query params
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

    try:
        # Prepare headers with API key if available
        headers = {}
        if API_KEY:
            headers['x-api-key'] = API_KEY
            logger.info("Using Semantic Scholar API key")
        
        # Make the request
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.info(f"Querying Semantic Scholar API with params: {params}")
            response = await client.get(BASE_URL, params=params, headers=headers)
            response.raise_for_status()  # Raise exception for non-200 responses
            data = response.json()
    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
        logger.error(error_msg)
        return f"Error: Failed to retrieve data from Semantic Scholar API. {error_msg}"
    except httpx.RequestError as e:
        error_msg = f"Request error occurred: {str(e)}"
        logger.error(error_msg)
        return f"Error: Failed to connect to Semantic Scholar API. {error_msg}"
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        return f"Error: An unexpected error occurred. {error_msg}"

    if not data.get('data'):
        return "No papers found matching your search criteria."

    # Format the results
    markdown = f"## Academic Search Results\n"
    markdown += f"📚 Found {data.get('total', 0):,} papers. Showing {len(data['data'])} recent results:\n\n"

    for index, paper in enumerate(data['data'], 1):
        # Title with year
        markdown += f"### {index}. {paper.get('title', 'Untitled')} ({paper.get('year', 'N/A')})\n\n"

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
                name_parts = author.get('name', '').split()
                if name_parts:
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

if __name__ == "__main__":
    logger.info("Starting Semantic Scholar MCP server...")
    mcp.run()
