from pathlib import Path
import typer
from miner.client import GitHubClient
from miner.processor import RepositoryProcessor

app = typer.Typer(
    help="Miner: CLI para identificar repositorios con GitHub Agentic Workflows (GH-AW)."
)


@app.command()
def main(
    input_file: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Archivo CSV de entrada con los repositorios candidatos.",
    ),
    output: Path = typer.Option(
        "repositorios_ghaw.csv",
        "--output",
        "-o",
        help="Ruta del archivo CSV de salida con los repositorios filtrados.",
    ),
    repo_column: str = typer.Option(
        "name",
        "--column",
        "-c",
        help="Nombre de la columna en el CSV que contiene el formato 'usuario/repositorio'.",
    ),
    workers: int = typer.Option(
        10, "--workers", "-w", help="Número de hilos concurrentes."
    ),
):
    """Procesa el CSV de entrada y genera uno de salida únicamente con repositorios GH-AW."""
    typer.echo(f"Procesando: {input_file}")

    try:
        client = GitHubClient()
        processor = RepositoryProcessor(
            client=client, repo_column=repo_column, max_workers=workers
        )

        total_match = processor.process(
            str(input_file), str(output)
        )

        typer.secho(
            f"Proceso finalizado con éxito. Se encontraron {total_match} repositorios con GH-AW.",
            fg=typer.colors.GREEN,
            bold=True,
        )
        typer.echo(f"Resultado guardado en: {output}")

    except Exception as e:
        typer.secho(f"Error durante la ejecución: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()