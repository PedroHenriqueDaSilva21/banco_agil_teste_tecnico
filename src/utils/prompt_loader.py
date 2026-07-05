from pathlib import Path


def load_prompt(filename: str) -> str:
    """
    Carrega um arquivo de prompt Markdown a partir do diretório padrão de prompts.

    Args:
        filename: Nome do arquivo de prompt (ex: 'triage.md').

    Returns:
        Conteúdo do arquivo como string.

    Raises:
        FileNotFoundError: Se o arquivo de prompt não for encontrado.
    """
    prompts_dir = Path(__file__).resolve().parent.parent / "agents" / "prompts"
    prompt_path = prompts_dir / filename

    if not prompt_path.exists() and len(Path(filename).parts) == 1:
        matches = list(prompts_dir.rglob(filename))
        if len(matches) == 1:
            prompt_path = matches[0]

    if not prompt_path.exists():
        raise FileNotFoundError(f"Arquivo de prompt não encontrado: {prompt_path}")

    return prompt_path.read_text(encoding="utf-8").strip()
