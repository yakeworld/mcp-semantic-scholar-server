from mcp.server.fastmcp import FastMCP
import httpx
from typing import Optional, List, Dict, Any
import os
from pydantic import Field, BaseModel
import logging
import json
from datetime import datetime

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

# Constants - Expanded fields list to get more information
FIELDS = ','.join([
    'title', 'year', 'authors', 'venue', 'citationCount', 'externalIds', 
    'abstract', 'url', 'journal', 'fieldsOfStudy', 'publicationTypes', 
    'publicationDate', 'referenceCount', 'influentialCitationCount', 
    'isOpenAccess', 's2FieldsOfStudy', 'publicationVenue', 'tldr'
])
BASE_URL = 'https://api.semanticscholar.org/graph/v1/paper/search'
AUTHOR_URL = 'https://api.semanticscholar.org/graph/v1/author/search'
PAPER_DETAILS_URL = 'https://api.semanticscholar.org/graph/v1/paper/'

class SearchFilter(BaseModel):
    """Model for advanced search filters"""
    venue: Optional[str] = Field(None, description="Filter by publication venue")
    fields_of_study: Optional[List[str]] = Field(None, description="Filter by fields of study")
    publication_types: Optional[List[str]] = Field(None, description="Filter by publication types")
    min_citation_count: Optional[int] = Field(None, description="Minimum citation count")
    is_open_access: Optional[bool] = Field(None, description="Filter for open access papers only")

@mcp.tool()
async def search_papers_via_semanticscholar(
    keyword: str = Field(..., description="Search query for academic papers (e.g., 'quantum computing')"),
    limit: int = Field(10, description="Maximum number of results to return", ge=1, le=100),
    year_from: Optional[int] = Field(None, description="Filter papers from this year onwards"),
    year_to: Optional[int] = Field(None, description="Filter papers up to this year"),
    sort_by: str = Field("relevance", description="Sort results by: relevance, citationCount, year"),
    advanced_filters: Optional[str] = Field(None, description="JSON string with advanced filters (venue, fields_of_study, etc.)")
) -> str:
    """
    Search for academic papers and research articles across multiple disciplines using Semantic Scholar's database.
    Returns detailed results with titles, authors, abstracts, citations, fields of study, and more.
    
    Example advanced_filters: '{"venue":"Nature", "fields_of_study":["Computer Science"], "min_citation_count":10, "is_open_access":true}'
    """
    # Build the query params
    params = {
        'query': keyword,
        'limit': str(limit),
        'fields': FIELDS
    }
    
    # Add year filter
    if year_from or year_to:
        year_filter = ""
        if year_from and year_to:
            year_filter = f"{year_from}-{year_to}"
        elif year_from:
            year_filter = f"{year_from}-"
        elif year_to:
            year_filter = f"-{year_to}"
        params['year'] = year_filter
    
    # Add sorting
    if sort_by and sort_by != "relevance":
        if sort_by == "citationCount":
            params['sort'] = "citationCount:desc"
        elif sort_by == "year":
            params['sort'] = "year:desc"
    
    # Process advanced filters if provided
    filters = {}
    if advanced_filters:
        try:
            filter_dict = json.loads(advanced_filters)
            for key, value in filter_dict.items():
                if key == "venue" and value:
                    filters["venue"] = value
                elif key == "fields_of_study" and value:
                    filters["fieldsOfStudy"] = {"$in": value}
                elif key == "publication_types" and value:
                    filters["publicationTypes"] = {"$in": value}
                elif key == "min_citation_count" and value:
                    filters["citationCount"] = {"$gte": value}
                elif key == "is_open_access" and value:
                    filters["isOpenAccess"] = value
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in advanced_filters: {advanced_filters}")
    
    if filters:
        params['filter'] = json.dumps(filters)

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
            
            # Fetch additional details for top papers if needed
            if data.get('data') and len(data['data']) > 0:
                for paper in data['data']:
                    if paper.get('paperId'):
                        try:
                            # Get more detailed paper information including references and citations
                            details_url = f"{PAPER_DETAILS_URL}{paper['paperId']}?fields={FIELDS},references.limit(5),citations.limit(5)"
                            details_response = await client.get(details_url, headers=headers)
                            if details_response.status_code == 200:
                                paper_details = details_response.json()
                                # Add additional information to the paper object
                                paper['references'] = paper_details.get('references', [])
                                paper['citations'] = paper_details.get('citations', [])
                                paper['tldr'] = paper_details.get('tldr', {})
                        except Exception as e:
                            logger.warning(f"Failed to get details for paper {paper.get('paperId')}: {str(e)}")
                            
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

    # Format the results with more detailed information
    markdown = f"# Academic Search Results for '{keyword}'\n\n"
    markdown += f"📚 Found {data.get('total', 0):,} papers. Showing {len(data['data'])} results sorted by {sort_by}:\n\n"

    for index, paper in enumerate(data['data'], 1):
        # Title with year and publication type
        pub_types = paper.get('publicationTypes', [])
        pub_type_str = f" [{', '.join(pub_types[:2])}]" if pub_types else ""
        markdown += f"## {index}. {paper.get('title', 'Untitled')} ({paper.get('year', 'N/A')}){pub_type_str}\n\n"

        # Authors with more details
        if paper.get('authors'):
            markdown += "👥 **Authors:** "
            authors = paper['authors']
            author_names = []
            
            for i, author in enumerate(authors[:5]):
                author_name = author.get('name', '')
                author_id = author.get('authorId', '')
                
                if author_id:
                    author_names.append(f"[{author_name}](https://www.semanticscholar.org/author/{author_id})")
                else:
                    author_names.append(author_name)
            
            markdown += ', '.join(author_names)
            if len(paper['authors']) > 5:
                markdown += f' and {len(paper["authors"]) - 5} others'
            markdown += '\n\n'

        # Publication details
        venue = paper.get('venue', 'N/A')
        journal = paper.get('journal', {})
        journal_name = journal.get('name') if journal else None
        
        if journal_name:
            markdown += f"📍 **Journal:** {journal_name}\n"
        elif venue:
            markdown += f"📍 **Venue:** {venue}\n"
            
        # Publication date (more precise than just year)
        pub_date = paper.get('publicationDate', paper.get('year', 'N/A'))
        if pub_date and pub_date != paper.get('year', 'N/A'):
            try:
                # Try to format the date nicely
                date_obj = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                markdown += f"📅 **Published:** {date_obj.strftime('%B %d, %Y')}\n"
            except:
                markdown += f"📅 **Published:** {pub_date}\n"
                
        # Citation metrics
        citations = paper.get('citationCount', 0)
        influential_citations = paper.get('influentialCitationCount', 0)
        references = paper.get('referenceCount', 0)
        
        markdown += f"📊 **Citations:** {citations:,} total"
        if influential_citations:
            markdown += f", {influential_citations:,} influential"
        markdown += f"\n📚 **References:** {references:,}\n"

        # Fields of study
        if paper.get('fieldsOfStudy'):
            markdown += f"🔬 **Fields:** {', '.join(paper.get('fieldsOfStudy', []))}\n"
            
        # Open access status
        is_open = paper.get('isOpenAccess', False)
        markdown += f"🔓 **Open Access:** {'Yes' if is_open else 'No'}\n"

        # External IDs
        if paper.get('externalIds'):
            markdown += "🔗 **Identifiers:** "
            ids = []
            ext_ids = paper['externalIds']
            
            if ext_ids.get('DOI'):
                ids.append(f"DOI: [{ext_ids['DOI']}](https://doi.org/{ext_ids['DOI']})")
            if ext_ids.get('ArXiv'):
                ids.append(f"arXiv: [{ext_ids['ArXiv']}](https://arxiv.org/abs/{ext_ids['ArXiv']})")
            if ext_ids.get('PubMed'):
                ids.append(f"PubMed: {ext_ids['PubMed']}")
            if ext_ids.get('CorpusId'):
                ids.append(f"Corpus ID: {ext_ids['CorpusId']}")
                
            markdown += ", ".join(ids) + "\n"

        # TLDR (AI-generated summary if available)
        if paper.get('tldr') and paper['tldr'].get('text'):
            markdown += f"💡 **TL;DR:** {paper['tldr']['text']}\n"

        # Abstract
        if paper.get('abstract'):
            markdown += f"\n📝 **Abstract:**\n{paper['abstract']}\n"

        # Key citations
        if paper.get('citations') and len(paper['citations']) > 0:
            markdown += f"\n📣 **Key Citations:**\n"
            for i, citation in enumerate(paper['citations'][:3], 1):
                title = citation.get('title', 'Untitled')
                year = citation.get('year', 'N/A')
                authors = ', '.join([a.get('name', '') for a in citation.get('authors', [])][:3])
                if citation.get('authors', []) and len(citation['authors']) > 3:
                    authors += ' et al.'
                markdown += f"{i}. {title} ({year}) - {authors}\n"

        # Key references
        if paper.get('references') and len(paper['references']) > 0:
            markdown += f"\n📚 **Key References:**\n"
            for i, reference in enumerate(paper['references'][:3], 1):
                title = reference.get('title', 'Untitled')
                year = reference.get('year', 'N/A')
                authors = ', '.join([a.get('name', '') for a in reference.get('authors', [])][:3])
                if reference.get('authors', []) and len(reference['authors']) > 3:
                    authors += ' et al.'
                markdown += f"{i}. {title} ({year}) - {authors}\n"

        # URL
        if paper.get('url'):
            markdown += f"\n🌐 **Full Paper:** [View on Semantic Scholar]({paper['url']})\n"
        else:
            paper_id = paper.get('paperId')
            if paper_id:
                markdown += f"\n🌐 **Paper Link:** [View on Semantic Scholar](https://www.semanticscholar.org/paper/{paper_id})\n"

        # Citation format
        markdown += f"\n📋 **Citation:**\n```\n"
        authors_citation = ', '.join([a.get('name', '') for a in paper.get('authors', [])][:6])
        if paper.get('authors', []) and len(paper['authors']) > 6:
            authors_citation += ' et al.'
        
        journal_or_venue = journal_name if journal_name else venue
        markdown += f"{authors_citation}. ({paper.get('year', 'n.d.')}). {paper.get('title', 'Untitled')}. "
        
        if journal_or_venue:
            markdown += f"{journal_or_venue}. "
        
        if paper.get('externalIds', {}).get('DOI'):
            markdown += f"https://doi.org/{paper['externalIds']['DOI']}"
        
        markdown += "\n```\n"

        markdown += "\n---\n\n"

    # Add export options information
    markdown += "\n## 📥 Export Options\n\n"
    markdown += "To cite these papers in your research, you can use the following formats:\n\n"
    markdown += "- **APA**: Author, A. A., & Author, B. B. (Year). Title of article. *Journal Title*, Volume(Issue), page range. https://doi.org/xxxx\n"
    markdown += "- **MLA**: Author Surname, First Name. \"Title of Article.\" *Journal Title*, vol. number, no. number, Year, pp. range. DOI or URL.\n"
    markdown += "- **Chicago**: Author Surname, First Name. Year. \"Title of Article.\" *Journal Title* Volume, no. Issue (Year): Page range. DOI or URL.\n\n"
    markdown += "For more citation options or to download citations in BibTeX format, click on the paper links to visit Semantic Scholar.\n"

    return markdown

@mcp.tool()
async def get_paper_details(
    paper_id: str = Field(..., description="Semantic Scholar Paper ID or DOI"),
    include_references: bool = Field(True, description="Include paper references"),
    include_citations: bool = Field(True, description="Include paper citations")
) -> str:
    """
    Get detailed information about a specific academic paper using its Semantic Scholar ID or DOI.
    Returns comprehensive metadata, abstract, citations, references, and more.
    """
    # Determine if input is a DOI or a Semantic Scholar Paper ID
    if paper_id.startswith("10.") or "/" in paper_id:
        # It's likely a DOI
        endpoint = f"{PAPER_DETAILS_URL}DOI:{paper_id}"
    else:
        # Treat as Semantic Scholar ID
        endpoint = f"{PAPER_DETAILS_URL}{paper_id}"
    
    # Configure fields to retrieve
    fields_list = list(FIELDS.split(','))
    
    # Add citation and reference fields if requested
    if include_references:
        fields_list.append('references.limit(20)')
    
    if include_citations:
        fields_list.append('citations.limit(20)')
    
    fields_param = ','.join(fields_list)
    params = {'fields': fields_param}
    
    try:
        # Prepare headers with API key if available
        headers = {}
        if API_KEY:
            headers['x-api-key'] = API_KEY
        
        # Make the request
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.info(f"Fetching paper details for: {paper_id}")
            response = await client.get(endpoint, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
        logger.error(error_msg)
        return f"Error: Failed to retrieve paper details. {error_msg}"
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        return f"Error: An unexpected error occurred. {error_msg}"

    if not data:
        return "No paper found with the provided ID or DOI."

    # Format the detailed paper information
    markdown = f"# {data.get('title', 'Untitled Paper')}\n\n"
    
    # Publication information
    pub_year = data.get('year', 'N/A')
    pub_types = data.get('publicationTypes', [])
    pub_type_str = f" [{', '.join(pub_types)}]" if pub_types else ""
    
    markdown += f"**Published:** {pub_year}{pub_type_str}\n\n"
    
    # Authors with affiliations
    if data.get('authors'):
        markdown += "## 👥 Authors\n\n"
        for author in data['authors']:
            author_name = author.get('name', 'Unknown')
            author_id = author.get('authorId')
            
            if author_id:
                markdown += f"- [{author_name}](https://www.semanticscholar.org/author/{author_id})"
            else:
                markdown += f"- {author_name}"
                
            if author.get('affiliations'):
                markdown += f" ({', '.join(author['affiliations'])})"
            markdown += "\n"
        markdown += "\n"
    
    # Journal/Venue information
    journal = data.get('journal', {})
    venue = data.get('venue')
    
    if journal and journal.get('name'):
        markdown += f"**Journal:** {journal.get('name')}\n"
        if journal.get('volume'):
            markdown += f"**Volume:** {journal.get('volume')}"
            if journal.get('pages'):
                markdown += f", Pages: {journal.get('pages')}"
            markdown += "\n"
    elif venue:
        markdown += f"**Publication Venue:** {venue}\n"
    
    # Impact metrics
    citations = data.get('citationCount', 0)
    influential_citations = data.get('influentialCitationCount', 0)
    references = data.get('referenceCount', 0)
    
    markdown += f"## 📊 Impact Metrics\n\n"
    markdown += f"- **Total Citations:** {citations:,}\n"
    markdown += f"- **Influential Citations:** {influential_citations:,}\n"
    markdown += f"- **References:** {references:,}\n"
    
    # Open access status
    is_open = data.get('isOpenAccess', False)
    markdown += f"- **Open Access:** {'Yes ✓' if is_open else 'No ✗'}\n\n"
    
    # Identifiers section
    if data.get('externalIds'):
        markdown += "## 🔗 Identifiers\n\n"
        ext_ids = data['externalIds']
        
        if ext_ids.get('DOI'):
            markdown += f"- **DOI:** [{ext_ids['DOI']}](https://doi.org/{ext_ids['DOI']})\n"
        if ext_ids.get('ArXiv'):
            markdown += f"- **arXiv:** [{ext_ids['ArXiv']}](https://arxiv.org/abs/{ext_ids['ArXiv']})\n"
        if ext_ids.get('PubMed'):
            markdown += f"- **PubMed:** {ext_ids['PubMed']}\n"
        if ext_ids.get('DBLP'):
            markdown += f"- **DBLP:** {ext_ids['DBLP']}\n"
        if ext_ids.get('CorpusId'):
            markdown += f"- **Corpus ID:** {ext_ids['CorpusId']}\n"
        if data.get('paperId'):
            markdown += f"- **Semantic Scholar ID:** {data['paperId']}\n"
        markdown += "\n"
    
    # Fields of study
    if data.get('fieldsOfStudy'):
        markdown += f"## 🔬 Research Fields\n\n"
        for field in data.get('fieldsOfStudy', []):
            markdown += f"- {field}\n"
        markdown += "\n"
    
    # TLDR (AI-generated summary)
    if data.get('tldr') and data['tldr'].get('text'):
        markdown += f"## 💡 TL;DR\n\n"
        markdown += f"{data['tldr']['text']}\n\n"
    
    # Abstract
    if data.get('abstract'):
        markdown += f"## 📝 Abstract\n\n"
        markdown += f"{data['abstract']}\n\n"
    
    # Key citations section
    if include_citations and data.get('citations') and len(data['citations']) > 0:
        markdown += f"## 📣 Key Citations ({min(len(data['citations']), 20)} of {citations:,})\n\n"
        for i, citation in enumerate(data['citations'], 1):
            title = citation.get('title', 'Untitled')
            year = citation.get('year', 'N/A')
            cite_count = citation.get('citationCount', 0)
            
            markdown += f"### {i}. {title} ({year}) - {cite_count:,} citations\n"
            
            if citation.get('authors'):
                authors = ', '.join([a.get('name', '') for a in citation.get('authors', [])][:5])
                if len(citation['authors']) > 5:
                    authors += ' et al.'
                markdown += f"**Authors:** {authors}\n"
            
            if citation.get('abstract'):
                abstract = citation['abstract']
                if len(abstract) > 200:
                    abstract = abstract[:200] + "..."
                markdown += f"**Abstract:** {abstract}\n"
            
            if citation.get('url'):
                markdown += f"[View Paper]({citation['url']})\n"
            
            markdown += "\n"
    
    # References section
    if include_references and data.get('references') and len(data['references']) > 0:
        markdown += f"## 📚 References ({min(len(data['references']), 20)} of {references:,})\n\n"
        for i, reference in enumerate(data['references'], 1):
            title = reference.get('title', 'Untitled')
            year = reference.get('year', 'N/A')
            
            markdown += f"{i}. **{title}** ({year})\n"
            
            if reference.get('authors'):
                authors = ', '.join([a.get('name', '') for a in reference.get('authors', [])][:3])
                if len(reference['authors']) > 3:
                    authors += ' et al.'
                markdown += f"   *{authors}*\n"
            
            if reference.get('url'):
                markdown += f"   [View Paper]({reference['url']})\n"
            
            markdown += "\n"
    
    # Paper URL
    if data.get('url'):
        markdown += f"## 🌐 Access\n\n"
        markdown += f"[View Full Paper on Semantic Scholar]({data['url']})\n\n"
    
    # Citation formats
    markdown += f"## 📋 Citation Formats\n\n"
    
    # Extract citation information
    authors_list = [a.get('name', '') for a in data.get('authors', [])]
    if not authors_list:
        authors_list = ['Unknown Author']
    
    title = data.get('title', 'Untitled')
    year = data.get('year', 'n.d.')
    journal_name = journal.get('name') if journal else (venue or 'Unknown Journal')
    volume = journal.get('volume', '') if journal else ''
    issue = journal.get('issue', '') if journal else ''
    pages = journal.get('pages', '') if journal else ''
    doi = data.get('externalIds', {}).get('DOI', '')
    
    # APA format
    markdown += "**APA:**\n```\n"
    if len(authors_list) == 1:
        markdown += f"{authors_list[0]}. "
    elif len(authors_list) == 2:
        markdown += f"{authors_list[0]} & {authors_list[1]}. "
    elif len(authors_list) > 2:
        markdown += f"{authors_list[0]} et al. "
    
    markdown += f"({year}). {title}. "
    
    if journal_name != 'Unknown Journal':
        markdown += f"*{journal_name}*"
        if volume:
            markdown += f", {volume}"
            if issue:
                markdown += f"({issue})"
        if pages:
            markdown += f", {pages}"
    
    if doi:
        markdown += f". https://doi.org/{doi}"
    
    markdown += "\n```\n\n"
    
    # MLA format
    markdown += "**MLA:**\n```\n"
    if authors_list and authors_list[0]:
        # Split first author's name
        name_parts = authors_list[0].split()
        if len(name_parts) > 1:
            last_name = name_parts[-1]
            first_names = ' '.join(name_parts[:-1])
            markdown += f"{last_name}, {first_names}"
        else:
            markdown += authors_list[0]
        
        if len(authors_list) > 1:
            markdown += ", et al"
    else:
        markdown += "Unknown Author"
    
    markdown += f". \"{title}.\" *{journal_name}*"
    
    if volume:
        markdown += f", vol. {volume}"
    if issue:
        markdown += f", no. {issue}"
    if year != 'n.d.':
        markdown += f", {year}"
    if pages:
        markdown += f", pp. {pages}"
    if doi:
        markdown += f", doi:{doi}"
    
    markdown += ".\n```\n\n"
    
    # BibTeX format
    markdown += "**BibTeX:**\n```bibtex\n"
    
    # Determine entry type
    entry_type = "article"
    if "Conference" in journal_name or "Proceedings" in journal_name:
        entry_type = "inproceedings"
    elif "Thesis" in journal_name:
        entry_type = "phdthesis"
    elif not journal.get('name') and not volume:
        entry_type = "misc"
    
    # Create citation key
    first_author_last = "unknown"
    if authors_list and authors_list[0]:
        first_author_parts = authors_list[0].split()
        if first_author_parts:
            first_author_last = first_author_parts[-1].lower()
    
    citation_key = f"{first_author_last}{year}"
    
    markdown += f"@{entry_type}{{{citation_key},\n"
    markdown += f"  title = {{{title}}},\n"
    
    if authors_list:
        markdown += f"  author = {{{' and '.join(authors_list)}}},\n"
    
    markdown += f"  year = {{{year}}},\n"
    
    if journal.get('name'):
        markdown += f"  journal = {{{journal.get('name')}}},\n"
    elif venue:
        markdown += f"  booktitle = {{{venue}}},\n"
    
    if volume:
        markdown += f"  volume = {{{volume}}},\n"
    if issue:
        markdown += f"  number = {{{issue}}},\n"
    if pages:
        markdown += f"  pages = {{{pages}}},\n"
    if doi:
        markdown += f"  doi = {{{doi}}},\n"
    if data.get('url'):
        markdown += f"  url = {{{data.get('url')}}},\n"
    
    markdown += "}\n```\n"
    
    return markdown

@mcp.tool()
async def search_authors(
    author_name: str = Field(..., description="Author name to search for"),
    limit: int = Field(10, description="Maximum number of results to return", ge=1, le=50)
) -> str:
    """
    Search for authors in Semantic Scholar by name.
    Returns information about matching authors including their publications, h-index, and citation count.
    """
    params = {
        'query': author_name,
        'limit': str(limit),
        'fields': 'name,aliases,affiliations,homepage,paperCount,citationCount,hIndex,url'
    }
    
    try:
        headers = {}
        if API_KEY:
            headers['x-api-key'] = API_KEY
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(AUTHOR_URL, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        logger.error(f"Error searching for authors: {str(e)}")
        return f"Error: Failed to search for authors. {str(e)}"
    
    if not data.get('data'):
        return f"No authors found matching '{author_name}'."
    
    markdown = f"# Author Search Results for '{author_name}'\n\n"
    markdown += f"Found {data.get('total', 0):,} authors. Showing top {len(data['data'])}:\n\n"
    
    for i, author in enumerate(data['data'], 1):
        name = author.get('name', 'Unknown')
        author_id = author.get('authorId', '')
        
        markdown += f"## {i}. {name}\n\n"
        
        if author.get('aliases'):
            markdown += f"**Also known as:** {', '.join(author['aliases'])}\n"
        
        if author.get('affiliations'):
            markdown += f"**Affiliations:** {', '.join(author['affiliations'])}\n"
        
        # Metrics
        h_index = author.get('hIndex', 'N/A')
        citation_count = author.get('citationCount', 'N/A')
        paper_count = author.get('paperCount', 'N/A')
        
        markdown += "**Metrics:**\n"
        markdown += f"- H-index: {h_index}\n"
        markdown += f"- Total Citations: {citation_count:,}\n" if isinstance(citation_count, int) else f"- Total Citations: {citation_count}\n"
        markdown += f"- Publications: {paper_count:,}\n" if isinstance(paper_count, int) else f"- Publications: {paper_count}\n"
        
        if author.get('homepage'):
            markdown += f"**Homepage:** [{author['homepage']}]({author['homepage']})\n"
        
        if author.get('url'):
            markdown += f"**Semantic Scholar Profile:** [View Profile]({author['url']})\n"
        elif author_id:
            markdown += f"**Semantic Scholar Profile:** [View Profile](https://www.semanticscholar.org/author/{author_id})\n"
        
        markdown += "\n---\n\n"
    
    return markdown

if __name__ == "__main__":
    logger.info("Starting Semantic Scholar MCP server...")
    mcp.run()
