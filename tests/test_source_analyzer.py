import unittest

from truth_mirror.source_analyzer import SourceAnalyzer
from truth_mirror.models import EvidenceItem

class TestSourceAnalyzer(unittest.TestCase):
    def test_source_prioritization(self):
        analyzer = SourceAnalyzer()
        
        # Create a list of 20 relevant articles with varying source credibility
        relevant_articles = []
        for i in range(10):
            relevant_articles.append(EvidenceItem(
                publisher="Generic News",
                source_type="other",
                source_title=f"Generic News {i}",
                url_or_id=f"http://example.com/generic_{i}",
                excerpt="Some random text",
                date="2025-01-01"
            ))
            
        relevant_articles.append(EvidenceItem(
            publisher="Wikipedia",
            source_type="database",
            source_title="Test Wikipedia",
            url_or_id="http://en.wikipedia.org/wiki/Test",
            excerpt="High quality text",
            date="2025-01-01"
        ))
        
        relevant_articles.append(EvidenceItem(
            publisher="Reuters",
            source_type="journalism",
            source_title="Test Reuters",
            url_or_id="http://reuters.com/test",
            excerpt="High quality news",
            date="2025-01-01"
        ))
        
        for i in range(8):
            relevant_articles.append(EvidenceItem(
                publisher="Random Blog",
                source_type="other",
                source_title=f"Blog {i}",
                url_or_id=f"http://blog.com/random_{i}",
                excerpt="Blog text",
                date="2025-01-01"
            ))
            
        sorted_articles = analyzer._prioritize_and_cap(relevant_articles, max_sources=15)
        
        # Should be exactly 15 articles
        self.assertEqual(len(sorted_articles), 15)
        
        # Wikipedia and Reuters MUST be in the final 15
        sources = [a.publisher for a in sorted_articles]
        self.assertIn("Wikipedia", sources)
        self.assertIn("Reuters", sources)

if __name__ == '__main__':
    unittest.main()
