from pathlib import Path
import toml
import mistune
from math import ceil
from tools.insert_template import insert_data
from mwc.counter import count_words_in_markdown
import shutil
from datetime import datetime

# Constants
WORDS_PER_MINUTE = 190  # Average reading speed
DEFAULT_IMG_DIR = "assets/img/"
RECENT_ARTICLE_NUMBER = 3

class NotesRenderer:
    """Handles the rendering of notes/PDF links."""

    @staticmethod
    def create_note_item(data: dict) -> str:
        """Creates HTML for a note/PDF item."""
        return f"""
        <div class="note-item">
            <div class="note-content">
                <span>{data['date']}</span> &bull;
                <a href="notes/{data['filename']}" class="note-title">
                    {data['display_name']}
                </a>
            </div>
        </div>
        """

    @staticmethod
    def create_section(data: dict) -> str:
        """Creates HTML for a section of notes."""
        return f"""
        <div class="notes-section">
            <h2 class="section-title">{data['title']}</h2>
            <div class="section-content">
                {data['notes']}
            </div>
        </div>
        """


class NotesProcessor:
    """Handles the processing of PDF files in the notes directory."""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.config = self._load_config()
        self.notes_dir = root_dir / self.config["directories"]["notes"]
        self.public_notes_dir = root_dir / "public/notes"

    def _load_config(self) -> dict:
        """Loads configuration from toml file."""
        with open(self.root_dir / "config.toml") as f:
            return toml.load(f)

    def _get_display_name(self, filename: str) -> str:
        """Converts filename to display name."""
        return filename.replace('.pdf', '').replace('_', ' ').title()

    def _format_section_title(self, directory_name: str) -> str:
        """Formats directory name to section title."""
        return directory_name.replace('_', ' ').title()

    def _process_single_note(self, pdf_path: Path, relative_to: Path) -> dict:
        """Processes a single PDF file."""
        stats = pdf_path.stat()
        relative_path = str(pdf_path.relative_to(relative_to))

        return {
            'filename': pdf_path.name,
            'relative_path': relative_path,
            'display_name': self._get_display_name(pdf_path.name),
            'date': datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d'),
        }

    def process_notes(self) -> dict:
        """Processes all PDF files in the notes directory."""
        self.public_notes_dir.mkdir(exist_ok=True)
        sections = {}

        # Process root directory
        for pdf_file in self.notes_dir.glob('*.pdf'):
            sections.setdefault('General', []).append(self._process_single_note(pdf_file, self.notes_dir))
            shutil.copy2(pdf_file, self.public_notes_dir / pdf_file.name)

        # Process subdirectories
        for directory in self.notes_dir.iterdir():
            if directory.is_dir():
                section_name = self._format_section_title(directory.name)
                sections[section_name] = []

                # Process PDFs in this section
                for pdf_file in directory.glob('**/*.pdf'):
                    sections[section_name].append(self._process_single_note(pdf_file, self.notes_dir))
                    dest_path = self.public_notes_dir / pdf_file.relative_to(self.notes_dir)
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(pdf_file, dest_path)

        # Sort notes in each section by date
        for section in sections.values():
            section.sort(key=lambda x: x['date'], reverse=True)

        return sections


class ArticleRenderer:
    """Handles the rendering of article cards and items."""

    @staticmethod
    def create_tag(data: dict) -> str:
        """Creates HTML for a tag item."""
        return f"""
        <div class="tag-item">
            <a class="light-text larger" href="tags/{data['tag name']}.html">
                <div class="tag-name">{data['tag name']}</div>
            </a>
            <span>&bull;</span>
            <div class="tag-count light-text-dim smol">{data['article count']}</div>
        </div>
        """

    @staticmethod
    def create_article_card(data: dict) -> str:
        """Creates HTML for an article card view."""
        return f"""
        <div class="article-card">
            <div class="article-thumbnail">
                <img src="{data['thumbnail']}" alt="Article Thumbnail">
            </div>
            <div class="article-content">
                <a href="articles/{data['id']}.html"><h2 class="article-title">{data['title']}</h2></a>
                <div class="article-meta-row">
                    <div class="article-meta">
                        <span>{data['date']}</span> &bull;
                        <span>{data['word count']} words</span> &bull;
                        <span>{data['reading time']} mins</span>
                    </div>
                </div>
                <div class="article-tags">{data['tags']}</div>
            </div>
        </div>
        """

    @staticmethod
    def create_article_item(data: dict) -> str:
        """Creates HTML for an article list item."""
        return f"""
        <div class="article-item">
            <div class="article-thumbnail">
                <img src="{data['thumbnail']}" alt="Article Thumbnail">
            </div>
            <div class="article-content">
                <a href="articles/{data['id']}.html"><h2 class="article-title">{data['title']}</h2></a>
                <div class="article-meta">
                    <span>{data['date']}</span> &bull;
                    <span>{data['word count']} words</span> &bull;
                    <span>{data['reading time']} mins</span>
                </div>
                <div class="article-tags">{data['tags']}</div>
            </div>
        </div>
        """


class ArticleProcessor:
    """Handles the processing of article files and metadata."""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.config = self._load_config()
        self.articles_dir = self.root_dir / self.config["directories"]["articles"]
        self.public_articles_dir = self.root_dir / "public/articles"

        self.public_tags_dir = self.root_dir / "public/tags"

    def _load_config(self) -> dict:
        """Loads configuration from toml file."""
        with open(self.root_dir / "config.toml") as f:
            return toml.load(f)

    def process_articles(self) -> list:
        """Processes all articles in the articles directory."""
        articles = self.articles_dir.glob('*')
        self.public_articles_dir.mkdir(exist_ok=True)
        parsed_list = [self._process_single_article(article) for article in articles]
        return sorted(parsed_list, key=lambda x: x["date"])

    def _process_single_article(self, article_path: Path) -> dict:
        """Processes a single article."""
        with open(article_path / "meta.toml") as f:
            metadata = toml.load(f)

        with open(article_path / "article.md") as f:
            content = f.read()
            word_count = count_words_in_markdown(content)

        metadata.update({
            "article": mistune.html(content),
            "word count": word_count,
            "reading time": ceil(word_count / WORDS_PER_MINUTE),
            "raw_tags": metadata["tags"],
            "tags": "".join([f'<span onclick="window.open(\'/tags/{t}.html\')">{t}</span>' for t in metadata["tags"]]),
            "thumbnail": DEFAULT_IMG_DIR + metadata['thumbnail']
        })

        self._generate_article_page(metadata)
        return metadata

    def _generate_article_page(self, article_data: dict):
        """Generates individual article page."""
        template_path = self.root_dir / "template/article-page.html"
        output_path = self.root_dir / f"public/articles/{article_data['id']}.html"
        insert_data(template_path, output_path, article_data)

    def process_tags_info(self, article_data: list[dict]) -> dict:
        """Processes tags information and returns dictionary of tag -> article IDs mapping."""
        tags_data = {}
        for article_metadata in article_data:
            for tag in article_metadata["raw_tags"]:
                if tag not in tags_data:
                    tags_data[tag] = {'articles': [], 'count': 0}
                tags_data[tag]['articles'].append(article_metadata)
                tags_data[tag]['count'] += 1
        return tags_data

    def generate_tag_pages(self, tags_data: dict, renderer: ArticleRenderer):
        """Generates individual pages for each tag."""
        template_path = self.root_dir / "template/tag-articles.html"
        self.public_tags_dir.mkdir(exist_ok=True)

        for tag_name, tag_info in tags_data.items():
            articles = sorted(tag_info['articles'], key=lambda x: x["date"], reverse=True)
            article_cards = [renderer.create_article_card(article) for article in articles]

            output_path = self.public_tags_dir / f"{tag_name}.html"
            insert_data(
                template_path,
                output_path,
                {
                    "articles": "".join(article_cards),
                    "title": f"Articles tagged with '{tag_name}'"
                }
            )


def main():
    """Main function to run the article processing and page generation."""
    root_dir = Path("../")
    processor = ArticleProcessor(root_dir)
    renderer = ArticleRenderer()
    notes_processor = NotesProcessor(root_dir)
    notes_renderer = NotesRenderer()

    # Copy assets
    shutil.copytree(root_dir / "template/assets", root_dir / "public/assets", dirs_exist_ok=True)

    # Process articles and tags
    processed_articles = processor.process_articles()
    processed_tags = processor.process_tags_info(processed_articles)

    # Generate article lists
    articles_cards = [renderer.create_article_card(article) for article in processed_articles]
    articles_items = [renderer.create_article_item(article) for article in processed_articles[:RECENT_ARTICLE_NUMBER]]

    # Generate tag list
    tags = [
        renderer.create_tag({'tag name': key, 'article count': str(value['count'])})
        for key, value in sorted(processed_tags.items())
    ]

    # Generate tag pages
    processor.generate_tag_pages(processed_tags, renderer)

    # Generate index and articles pages
    insert_data(root_dir / "template/articles.html", root_dir / "public/articles/index.html", {"articles": "".join(articles_cards)})
    insert_data(root_dir / "template/index.html", root_dir / "public/index.html", {"articles": "".join(articles_items)})
    insert_data(root_dir / "template/tags.html", root_dir / "public/tags/index.html", {"tags": "".join(tags)})

    # Process notes
    processed_sections = notes_processor.process_notes()
    sections_html = [
        notes_renderer.create_section({
            'title': section_name,
            'notes': ''.join(notes_renderer.create_note_item(note) for note in notes),
        }) for section_name, notes in processed_sections.items()
    ]

    # Generate notes page
    insert_data(root_dir / "template/notes.html", root_dir / "public/notes/index.html", {"notes": ''.join(sections_html)})


if __name__ == '__main__':
    main()
