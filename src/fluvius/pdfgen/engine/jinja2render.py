from typing import Any, Dict

import jinja2

from fii_pdfgen import config


class Jinja2TemplateRenderer(object):
    def __init__(self, searchpath):
        self.template_loader = jinja2.FileSystemLoader(searchpath=searchpath)
        self.template_env = jinja2.Environment(loader=self.template_loader)

    def add_filter(self, name, func):
        self.template_env.filters[name] = func

    def add_global(self, key, value):
        self.template_env.globals[key] = value

    def render(self, template_id, data: Dict[str, Any]):
        template = self.template_env.get_template(template_id)
        return str(template.render(**data))


jinja2renderer = Jinja2TemplateRenderer(config.TEMPLATE_DIR)
