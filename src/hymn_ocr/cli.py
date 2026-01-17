"""Command-line interface for hymn-ocr."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax

from hymn_ocr.pdf_processor import get_page_count
from hymn_ocr.pipeline import pdf_to_hymnbook, process_pdf
from hymn_ocr.yaml_generator import generate_yaml, preview_yaml, save_yaml

app = typer.Typer(
    name="hymn-ocr",
    help="Convert PDF hymnals to YAML using OCR and computer vision.",
    add_completion=False,
)

console = Console()


def parse_page_range(pages: Optional[str]) -> tuple[Optional[int], Optional[int]]:
    """Parse page range string like '2-10' or '5'."""
    if not pages:
        return None, None

    if "-" in pages:
        parts = pages.split("-")
        return int(parts[0]), int(parts[1])
    else:
        page = int(pages)
        return page, page


@app.command()
def convert(
    pdf_path: Path = typer.Argument(
        ...,
        help="Path to the PDF file to convert.",
        exists=True,
        dir_okay=False,
    ),
    output: Optional[Path] = typer.Option(
        None,
        "-o",
        "--output",
        help="Output YAML file path. If not specified, prints to stdout.",
    ),
    preview: bool = typer.Option(
        False,
        "--preview",
        help="Show preview of output without saving.",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable debug mode with extra output.",
    ),
    pages: Optional[str] = typer.Option(
        None,
        "--pages",
        help="Page range to process (e.g., '2-10' or '5').",
    ),
    dpi: int = typer.Option(
        300,
        "--dpi",
        help="DPI for PDF conversion.",
    ),
    name: str = typer.Option(
        "Hymn Book",
        "--name",
        help="Name of the hymn book.",
    ),
    owner: str = typer.Option(
        "Unknown",
        "--owner",
        help="Owner's name.",
    ),
):
    """
    Convert a PDF hymnal to YAML format.

    Examples:
        hymn-ocr convert hinario.pdf -o hinario.yaml
        hymn-ocr convert hinario.pdf --preview
        hymn-ocr convert hinario.pdf --pages 2-10 -o output.yaml
    """
    first_page, last_page = parse_page_range(pages)

    # Get page count for progress
    total_pages = get_page_count(pdf_path)
    if first_page:
        start = first_page
    else:
        start = 1
    if last_page:
        end = last_page
    else:
        end = total_pages

    pages_to_process = end - start + 1

    console.print(f"\n[bold]Processing:[/bold] {pdf_path.name}")
    console.print(f"[dim]Pages: {start}-{end} ({pages_to_process} pages)[/dim]")
    console.print()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Converting PDF to images...", total=None)

        def on_progress(current: int, total: int):
            progress.update(
                task,
                description=f"Processing page {current}/{total}...",
            )

        hymnbook = pdf_to_hymnbook(
            pdf_path,
            name=name,
            owner_name=owner,
            dpi=dpi,
            first_page=first_page,
            last_page=last_page,
            progress_callback=on_progress,
        )

        progress.update(task, description="Done!")

    # Summary
    console.print()
    console.print(f"[green]Extracted {len(hymnbook.hymns)} hymns[/green]")

    if debug:
        console.print("\n[bold]Hymns found:[/bold]")
        for hymn in hymnbook.hymns:
            console.print(f"  {hymn.number}. {hymn.title}")

    # Output
    if preview:
        console.print("\n[bold]Preview:[/bold]\n")
        yaml_preview = preview_yaml(hymnbook, max_hymns=3)
        syntax = Syntax(yaml_preview, "yaml", theme="monokai")
        console.print(syntax)
    elif output:
        save_yaml(hymnbook, output)
        console.print(f"\n[green]Saved to:[/green] {output}")
    else:
        yaml_content = generate_yaml(hymnbook)
        console.print("\n")
        syntax = Syntax(yaml_content, "yaml", theme="monokai")
        console.print(syntax)


@app.command()
def info(
    pdf_path: Path = typer.Argument(
        ...,
        help="Path to the PDF file.",
        exists=True,
        dir_okay=False,
    ),
):
    """
    Show information about a PDF file.
    """
    page_count = get_page_count(pdf_path)

    console.print(f"\n[bold]File:[/bold] {pdf_path.name}")
    console.print(f"[bold]Pages:[/bold] {page_count}")


@app.command()
def debug_page(
    pdf_path: Path = typer.Argument(
        ...,
        help="Path to the PDF file.",
        exists=True,
        dir_okay=False,
    ),
    page: int = typer.Argument(
        ...,
        help="Page number to debug (1-indexed).",
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "-o",
        "--output",
        help="Directory to save debug images.",
    ),
):
    """
    Debug OCR and zone detection for a single page.
    """
    from hymn_ocr.pdf_processor import convert_pdf_to_images
    from hymn_ocr.zone_detector import pil_to_cv2, detect_zones, visualize_zones, cv2_to_pil

    console.print(f"\n[bold]Debugging page {page}...[/bold]\n")

    # Convert page to image
    images = convert_pdf_to_images(pdf_path, dpi=300, first_page=page, last_page=page)
    if not images:
        console.print("[red]Failed to convert page[/red]")
        raise typer.Exit(1)

    image = images[0]
    cv2_image = pil_to_cv2(image)

    # Detect zones
    zones = detect_zones(cv2_image)

    console.print(f"[bold]Zone detection:[/bold]")
    console.print(f"  Is cover: {zones.is_cover}")
    if zones.header:
        console.print(f"  Header: y={zones.header.y_start}-{zones.header.y_end}")
    if zones.metadata:
        console.print(f"  Metadata: y={zones.metadata.y_start}-{zones.metadata.y_end}")
    if zones.body:
        console.print(f"  Body: y={zones.body.y_start}-{zones.body.y_end}")
    if zones.footer:
        console.print(f"  Footer: y={zones.footer.y_start}-{zones.footer.y_end}")

    # Save debug image if output dir specified
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save original
        image.save(output_dir / f"page_{page}_original.png")

        # Save with zones visualized
        debug_img = visualize_zones(cv2_image, zones)
        debug_pil = cv2_to_pil(debug_img)
        debug_pil.save(output_dir / f"page_{page}_zones.png")

        console.print(f"\n[green]Debug images saved to {output_dir}[/green]")


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
