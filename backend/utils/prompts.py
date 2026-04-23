from pathlib import Path
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

_env = Environment(loader=FileSystemLoader(str(PROMPTS_DIR)))


def render_prompt(template_name: str, **kwargs) -> str:
    """Render a Jinja2 prompt template by name with the given context variables.

    Args:
        template_name: Filename of the template in the prompts directory (e.g. 'domain_inference_user.j2')
        **kwargs: Template context variables

    Raises:
        FileNotFoundError: If the template does not exist
    """
    try:
        template = _env.get_template(template_name)
    except TemplateNotFound:
        raise FileNotFoundError(f"Prompt template not found: {PROMPTS_DIR / template_name}")

    return template.render(**kwargs).strip()
