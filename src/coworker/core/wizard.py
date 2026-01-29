import typer
import yaml
from rich.prompt import Prompt, Confirm
from rich.console import Console
from rich.panel import Panel
from . import config 

from .models import Config, OrganizationMode, CategoriesMode
from .storage import Workspace
from .i18n import t

console = Console()

def run_setup_wizard(workspace: Workspace):
    console.print(Panel.fit(t('cli.setup.title'), style="bold blue"))
    
    
    console.print(f"\n[bold]{t('cli.setup.step1_title')}[/bold]")
    org_choices = {
        "1": OrganizationMode.FOLDERS,
        "2": OrganizationMode.EXCEL,
        "3": OrganizationMode.BOTH
    }
    
    org_choice = Prompt.ask(
        t('cli.setup.step1_prompt'),
        choices=["1", "2", "3", "4"],
        default="3",
        show_choices=False
    )
    
    
    
    
    
    
    console.print(f"1. {t('cli.setup.step1_options.1')}")
    console.print(f"2. {t('cli.setup.step1_options.2')}")
    console.print(f"3. {t('cli.setup.step1_options.3')}")
    
    if org_choice == "4":
        console.print("[yellow]Custom logic not implemented yet. Defaulting to 'Both'.[/yellow]")
        mode = OrganizationMode.BOTH
    else:
        mode = org_choices.get(org_choice, OrganizationMode.BOTH)

    console.print(f"✅ Selected: [green]{mode.value}[/green]")

    
    console.print(f"\n[bold]{t('cli.setup.step2_title')}[/bold]")
    
    console.print(f"1. {t('cli.setup.step2_options.1')}")
    console.print(f"2. {t('cli.setup.step2_options.2')}")
    console.print(f"3. {t('cli.setup.step2_options.3')}")
    
    cat_choices = {
        "1": CategoriesMode.AUTO,
        "2": CategoriesMode.BUSINESS,
        "3": CategoriesMode.PERSONAL
    }
    
    cat_choice = Prompt.ask(
        t('cli.setup.step2_prompt'),
        choices=["1", "2", "3", "4"],
        default="1",
        show_choices=False
    )
    
    custom_cats = []
    if cat_choice == "4":
        cat_mode = CategoriesMode.CUSTOM
        input_cats = Prompt.ask("Enter categories separated by comma")
        custom_cats = [c.strip() for c in input_cats.split(",") if c.strip()]
    else:
        cat_mode = cat_choices.get(cat_choice, CategoriesMode.AUTO)
        
    console.print(f"✅ Selected: [green]{cat_mode.value}[/green]")

    
    
    
    
    
    
    
    
    
    config = Config(
        organization_mode=mode,
        categories_mode=cat_mode,
        custom_categories=custom_cats,
        
        lang=config.settings.i18n.lang 
    )
    
    
    workspace.system.mkdir(parents=True, exist_ok=True)
    
    with open(workspace.config_path, "w") as f:
        yaml.dump(config.model_dump(), f)
        
    console.print(f"\n{t('cli.setup.saved', path=workspace.config_path)}")
    console.print(t('cli.setup.ready'))
