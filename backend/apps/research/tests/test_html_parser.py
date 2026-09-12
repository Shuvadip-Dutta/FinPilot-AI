"""Tests for HTML document parsing, table extraction, and SEC markup handling."""

import io
from pathlib import Path
from django.test import SimpleTestCase

from apps.research.parsers import (
    ParsedDocument,
    extract_text_from_html,
    extract_text_from_pdf,
    extract_text_from_txt,
    parse_financial_document,
)


class HtmlParserTestSuite(SimpleTestCase):
    """Test suite covering HTML parsing, table structuring, security sanitization, and regression."""

    def test_basic_html_extraction(self):
        """Test extraction of headings, paragraphs, and lists."""
        html = """
        <!DOCTYPE html>
        <html>
        <body>
            <h1>Apple Inc. Form 10-K</h1>
            <h2>Item 1. Business</h2>
            <p>Apple designs, manufactures and markets smartphones, personal computers, tablets, wearables and accessories.</p>
            <p>Services include advertising, AppleCare, cloud services, digital content and payment services.</p>
        </body>
        </html>
        """
        doc = extract_text_from_html(html)
        self.assertIsInstance(doc, ParsedDocument)
        self.assertIn("Apple Inc. Form 10-K", doc.text)
        self.assertIn("Item 1. Business", doc.text)
        self.assertIn("Apple designs, manufactures and markets", doc.text)
        self.assertEqual(doc.page_count, 1)
        self.assertEqual(len(doc.pages), 1)

    def test_dangerous_and_non_content_tags_removed(self):
        """Test that script, style, head, noscript, svg, and iframe tags are stripped."""
        html = """
        <html>
        <head>
            <title>Secret Internal Title</title>
            <style>.hidden { display: none; } body { color: red; }</style>
            <script>alert('malicious script execution');</script>
        </head>
        <body>
            <noscript>Please enable JavaScript to view this report.</noscript>
            <svg><text>Ignored SVG Text</text></svg>
            <iframe src="https://example.com/ad"></iframe>
            <h1>Item 7. Management Discussion</h1>
            <p>Revenue increased 8% year-over-year.</p>
        </body>
        </html>
        """
        doc = extract_text_from_html(html)
        self.assertNotIn("alert('malicious", doc.text)
        self.assertNotIn(".hidden", doc.text)
        self.assertNotIn("Secret Internal Title", doc.text)
        self.assertNotIn("enable JavaScript", doc.text)
        self.assertNotIn("Ignored SVG", doc.text)
        self.assertIn("Item 7. Management Discussion", doc.text)
        self.assertIn("Revenue increased 8% year-over-year.", doc.text)

    def test_whitespace_and_newline_normalization(self):
        """Test that excessive whitespace and empty lines are collapsed."""
        html = """
        <div>
            <p>   Line one    with    multiple   spaces.   </p>
            <br><br><br><br>
            <p>Line two after multiple line breaks.</p>
        </div>
        """
        doc = extract_text_from_html(html)
        self.assertNotIn("   ", doc.text)
        # Should not have more than two consecutive newlines
        self.assertNotIn("\n\n\n", doc.text)
        self.assertIn("Line one with multiple spaces.", doc.text)
        self.assertIn("Line two after multiple line breaks.", doc.text)

    def test_table_extraction_with_headers_and_rows(self):
        """Test that financial tables are converted into clean pipe-delimited text."""
        html = """
        <div>
            <h3>Consolidated Statements of Operations</h3>
            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>2024</th>
                        <th>2023</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Total net sales</td>
                        <td>$391,035</td>
                        <td>$383,285</td>
                    </tr>
                    <tr>
                        <td>Operating income</td>
                        <td>$123,216</td>
                        <td>$114,301</td>
                    </tr>
                    <tr>
                        <td>Net income</td>
                        <td>$93,736</td>
                        <td>$96,995</td>
                    </tr>
                </tbody>
            </table>
        </div>
        """
        doc = extract_text_from_html(html)
        self.assertIn("Consolidated Statements of Operations", doc.text)
        self.assertIn("Metric | 2024 | 2023", doc.text)
        self.assertIn("Total net sales | $391,035 | $383,285", doc.text)
        self.assertIn("Operating income | $123,216 | $114,301", doc.text)
        self.assertIn("Net income | $93,736 | $96,995", doc.text)

    def test_table_with_nested_markup_and_spans(self):
        """Test table cells with nested formatting spans and non-breaking spaces."""
        html = """
        <table>
            <tr>
                <td><span><b>Cash and cash equivalents</b></span></td>
                <td><span style="font-weight:bold;">$ 29,965</span></td>
            </tr>
            <tr>
                <td><span>Marketable securities</span></td>
                <td><span>&nbsp;$ 31,586&nbsp;</span></td>
            </tr>
        </table>
        """
        doc = extract_text_from_html(html)
        self.assertIn("Cash and cash equivalents | $ 29,965", doc.text)
        self.assertIn("Marketable securities | $ 31,586", doc.text)

    def test_xbrl_namespaced_markup_tolerance(self):
        """Test that inline XBRL tags and XML namespaces are parsed and their content retained."""
        html = """
        <html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" xmlns:dei="http://xbrl.sec.gov/dei/2023">
        <body>
            <div>
                Company: <ix:nonNumeric contextRef="c1" name="dei:EntityRegistrantName">APPLE INC</ix:nonNumeric>
            </div>
            <div>
                CIK: <ix:nonNumeric contextRef="c1" name="dei:EntityCentralIndexKey">0000320193</ix:nonNumeric>
            </div>
            <div>
                Revenues: <ix:nonFraction unitRef="usd" decimals="-6" contextRef="c2" name="us-gaap:Revenue">391035000000</ix:nonFraction>
            </div>
        </body>
        </html>
        """
        doc = extract_text_from_html(html)
        self.assertIn("APPLE INC", doc.text)
        self.assertIn("0000320193", doc.text)
        self.assertIn("391035000000", doc.text)

    def test_bytes_and_binary_stream_input(self):
        """Test extract_text_from_html accepts bytes and BytesIO input."""
        html_content = b"<html><body><p>Direct bytes stream content.</p></body></html>"
        doc_from_bytes = extract_text_from_html(html_content)
        self.assertIn("Direct bytes stream content.", doc_from_bytes.text)

        stream = io.BytesIO(html_content)
        doc_from_stream = extract_text_from_html(stream)
        self.assertIn("Direct bytes stream content.", doc_from_stream.text)

    def test_empty_and_whitespace_only_html_raises_error(self):
        """Test that empty or unreadable HTML content raises ValueError."""
        with self.assertRaises(ValueError):
            extract_text_from_html("")

        with self.assertRaises(ValueError):
            extract_text_from_html("   \n\t  ")

        with self.assertRaises(ValueError):
            extract_text_from_html("<html><head><script>alert(1);</script></head><body></body></html>")

    def test_small_html_fallback(self):
        """Test that very short HTML snippet does not drop content."""
        html = "<b>Q3 Net Profit: $5.2B</b>"
        doc = extract_text_from_html(html)
        self.assertEqual(doc.text, "Q3 Net Profit: $5.2B")

    def test_parse_financial_document_html_dispatch(self):
        """Test parse_financial_document properly dispatches HTML files and content types."""
        html_content = "<html><body><h1>10-Q Filing</h1><p>Quarterly Report</p></body></html>"
        
        # Dispatch by content-type
        doc1 = parse_financial_document(html_content, content_type="text/html")
        self.assertIn("10-Q Filing", doc1.text)

        # Dispatch by filename extension
        doc2 = parse_financial_document(html_content, filename="filing_10k.htm")
        self.assertIn("10-Q Filing", doc2.text)

        doc3 = parse_financial_document(html_content, filename="report.xhtml")
        self.assertIn("10-Q Filing", doc3.text)

    def test_txt_and_pdf_regression(self):
        """Test that existing TXT parsing and unsupported formats behave as expected."""
        txt_content = "This is a plain text financial statement.\nRevenue: 100M"
        doc_txt = parse_financial_document(txt_content, content_type="text/plain")
        self.assertIn("plain text financial statement", doc_txt.text)
        self.assertEqual(doc_txt.page_count, 1)

        # Unsupported format
        with self.assertRaises(ValueError):
            parse_financial_document("test", content_type="image/png", filename="chart.png")
