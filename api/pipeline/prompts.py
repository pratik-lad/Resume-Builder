from functools import lru_cache

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from config import settings


@lru_cache(maxsize=1)
def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(settings.prompts)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render(name: str, **kwargs) -> str:
    return _env().get_template(name).render(**kwargs)
