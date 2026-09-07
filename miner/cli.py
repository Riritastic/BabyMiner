from pathlib import Path
import typer
from miner.client import GitHubClient
from miner.processor import DatasetProcessor

app = typer.Typer(
    help="Miner CLI: Extracción de GitHub Agentic Workflows hacia Parquet."
)


@app.command()
def build_dataset(
    input_file: Path = typer.Argument(
        ...,
        exists=True,
        help="CSV con repositorios candidatos.",
    ),
    output_dir: Path = typer.Option(
        Path("dataset_parquet"),
        "--output-dir",
        "-o",
        help="Directorio donde se guardarán las tablas en formato Parquet.",
    ),
    repo_column: str = typer.Option("name", "--column", "-c"),
):
    """Procesa repositorios GH-AW, extrae Frontmatter/Body y guarda tablas en Parquet."""
    typer.echo(f"Iniciando extracción desde {input_file}...")

    try:
        client = GitHubClient()
        processor = DatasetProcessor(client, repo_column=repo_column)

        stats = processor.process_and_export_parquet(
            str(input_file), output_dir
        )

        typer.secho(
            f"\n Dataset generado con éxito en '{output_dir}':",
            fg=typer.colors.GREEN,
            bold=True,
        )
        typer.echo(f"  • Repositorios: {stats['repositories']}")
        typer.echo(f"  • Workflows:    {stats['workflows']}")
        typer.echo(f"  • Cuerpos (.md): {stats['bodies']}")

    except Exception as e:
        typer.secho(f"Error procesando dataset: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()