"""
PDF Export Service for AURA Research Agent
Generates PDF documents from research essays with proper formatting and citations
"""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
from datetime import datetime

logger = logging.getLogger('aura.pdf_export')


class PDFExportService:
    """Service for exporting research essays to PDF format"""

    def __init__(self):
        """Initialize PDF export service"""
        try:
            from weasyprint import HTML, CSS
            self.HTML = HTML
            self.CSS = CSS
            self.weasyprint_available = True
        except ImportError:
            logger.warning("WeasyPrint not available, PDF export will use basic HTML fallback")
            self.weasyprint_available = False

    def generate_pdf(
        self,
        session_id: str,
        query: str,
        essay: str,
        citations: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
        citation_style: str = "APA"
    ) -> Optional[str]:
        """
        Generate PDF from essay content

        Args:
            session_id: Research session ID
            query: Original research query
            essay: Full essay text
            citations: List of citation dictionaries
            metadata: Additional metadata (word_count, synthesis, etc.)
            citation_style: Citation format (APA, MLA, Chicago)

        Returns:
            Path to generated PDF file, or None if generation failed
        """
        try:
            # Generate HTML content
            html_content = self._generate_html(
                query=query,
                essay=essay,
                citations=citations,
                metadata=metadata,
                citation_style=citation_style
            )

            # Create output directory if not exists
            output_dir = Path("output/pdfs")
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"research_{session_id}_{timestamp}.pdf"
            filepath = output_dir / filename

            # Try WeasyPrint first (better quality)
            if self.weasyprint_available:
                self._generate_with_weasyprint(html_content, str(filepath))
            else:
                # Fallback: generate HTML-only version (user can print to PDF)
                html_filepath = output_dir / f"research_{session_id}_{timestamp}.html"
                with open(html_filepath, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logger.info(f"HTML document generated (print to PDF): {html_filepath}")
                return str(html_filepath)

            logger.info(f"PDF generated successfully: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Failed to generate PDF for session {session_id}: {str(e)}", exc_info=True)
            return None

    def _generate_html(
        self,
        query: str,
        essay: str,
        citations: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]],
        citation_style: str
    ) -> str:
        """Generate HTML content for PDF"""

        # Extract metadata
        word_count = 0
        if metadata:
            word_count = metadata.get('word_count', 0)

        # Format bibliography based on citation style
        bibliography = self._format_bibliography(citations, citation_style)

        # Escape HTML content
        essay_html = self._escape_html(essay)
        query_html = self._escape_html(query)
        bibliography_html = self._escape_html(bibliography)

        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Research: {query_html}</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}

                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    background: white;
                    padding: 40px;
                    max-width: 900px;
                    margin: 0 auto;
                }}

                header {{
                    border-bottom: 3px solid #2d5a8c;
                    padding-bottom: 20px;
                    margin-bottom: 30px;
                }}

                h1 {{
                    font-size: 28px;
                    color: #1a3a5c;
                    margin-bottom: 10px;
                    word-wrap: break-word;
                }}

                .metadata {{
                    color: #666;
                    font-size: 12px;
                    margin-top: 10px;
                }}

                .metadata span {{
                    margin-right: 20px;
                }}

                .content {{
                    margin: 30px 0;
                    line-height: 1.8;
                }}

                .content p {{
                    margin-bottom: 15px;
                    text-align: justify;
                }}

                .bibliography {{
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 2px solid #ddd;
                }}

                .bibliography h2 {{
                    font-size: 18px;
                    color: #1a3a5c;
                    margin-bottom: 15px;
                    margin-top: 0;
                }}

                .citation {{
                    margin-bottom: 12px;
                    margin-left: 40px;
                    text-indent: -40px;
                    line-height: 1.5;
                    font-size: 12px;
                    color: #444;
                }}

                .footer {{
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    font-size: 10px;
                    color: #999;
                    text-align: center;
                }}

                @page {{
                    size: A4;
                    margin: 1in;
                }}

                @media print {{
                    body {{
                        padding: 0;
                    }}
                }}
            </style>
        </head>
        <body>
            <header>
                <h1>Research: {query_html}</h1>
                <div class="metadata">
                    <span>Generated: {datetime.now().strftime('%B %d, %Y')}</span>
                    <span>Citation Style: {citation_style}</span>
                    {f'<span>Word Count: {word_count}</span>' if word_count else ''}
                </div>
            </header>

            <div class="content">
                {essay_html}
            </div>

            {'<div class="bibliography"><h2>Bibliography</h2>' + bibliography_html + '</div>' if citations else ''}

            <div class="footer">
                <p>Generated by AURA Research Agent | www.aura-research.ai</p>
            </div>
        </body>
        </html>
        """

        return html

    def _format_bibliography(
        self,
        citations: List[Dict[str, Any]],
        citation_style: str
    ) -> str:
        """Format citations in specified style"""

        if citation_style == "APA":
            return self._format_apa(citations)
        elif citation_style == "MLA":
            return self._format_mla(citations)
        elif citation_style == "Chicago":
            return self._format_chicago(citations)
        else:
            return self._format_apa(citations)  # Default to APA

    def _format_apa(self, citations: List[Dict[str, Any]]) -> str:
        """Format citations in APA style"""
        html = ""
        for idx, citation in enumerate(citations, 1):
            authors = citation.get('authors', 'Unknown Author')
            year = citation.get('year', 'n.d.')
            title = citation.get('title', 'Untitled')
            journal = citation.get('journal', '')
            doi = citation.get('doi', '')
            url = citation.get('url', '')

            citation_text = f"{authors} ({year}). {title}."
            if journal:
                citation_text += f" {journal}."
            if doi:
                citation_text += f" https://doi.org/{doi}"
            elif url:
                citation_text += f" Retrieved from {url}"

            html += f'<div class="citation">{self._escape_html(citation_text)}</div>\n'

        return html

    def _format_mla(self, citations: List[Dict[str, Any]]) -> str:
        """Format citations in MLA style"""
        html = ""
        for idx, citation in enumerate(citations, 1):
            authors = citation.get('authors', 'Unknown Author')
            title = citation.get('title', 'Untitled')
            journal = citation.get('journal', '')
            year = citation.get('year', 'n.d.')
            url = citation.get('url', '')

            citation_text = f"{authors}. \"{title}.\" {journal}, {year}."
            if url:
                citation_text += f" {url}"

            html += f'<div class="citation">{self._escape_html(citation_text)}</div>\n'

        return html

    def _format_chicago(self, citations: List[Dict[str, Any]]) -> str:
        """Format citations in Chicago style"""
        html = ""
        for idx, citation in enumerate(citations, 1):
            authors = citation.get('authors', 'Unknown Author')
            title = citation.get('title', 'Untitled')
            journal = citation.get('journal', '')
            year = citation.get('year', 'n.d.')
            doi = citation.get('doi', '')

            citation_text = f"{authors}. \"{title}.\" {journal} ({year})."
            if doi:
                citation_text += f" https://doi.org/{doi}"

            html += f'<div class="citation">{self._escape_html(citation_text)}</div>\n'

        return html

    def _generate_with_weasyprint(self, html_content: str, output_path: str) -> None:
        """Generate PDF using WeasyPrint"""
        try:
            self.HTML(string=html_content).write_pdf(output_path)
        except Exception as e:
            logger.error(f"WeasyPrint generation failed: {str(e)}", exc_info=True)
            # Fallback to HTML
            html_path = output_path.replace('.pdf', '.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

    @staticmethod
    def _escape_html(text: str) -> str:
        """Escape HTML special characters"""
        if not text:
            return ""
        return (
            text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;')
        )


# Singleton instance
_pdf_export_service = None


def get_pdf_export_service() -> PDFExportService:
    """Get or create PDF export service singleton"""
    global _pdf_export_service
    if _pdf_export_service is None:
        _pdf_export_service = PDFExportService()
    return _pdf_export_service
