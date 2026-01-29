import typer
import yaml
from rich.prompt import Prompt, Confirm
from rich.console import Console
from rich.panel import Panel

from .models import Config, OrganizationMode, CategoriesMode
from .storage import Workspace

console = Console()

def run_setup_wizard(workspace: Workspace):
    console.print(Panel.fit("🤖 Welcome to Coworker Setup", style="bold blue"))
    
    # Step 1: Organization Preference
    console.print("\n[bold]Step 1: How would you like me to organize your receipts?[/bold]")
    org_choices = {
        "1": OrganizationMode.FOLDERS,
        "2": OrganizationMode.EXCEL,
        "3": OrganizationMode.BOTH
    }
    
    org_choice = Prompt.ask(
        "Choose an option",
        choices=["1", "2", "3", "4"],
        default="3",
        show_choices=False
    )
    
    if org_choice == "4":
        console.print("[yellow]Custom logic not implemented yet. Defaulting to 'Both'.[/yellow]")
        mode = OrganizationMode.BOTH
    else:
        # Map 1,2,3 to Enum, handle case where user might type 4 or Skip logic if we added it
        # Actually logic is correct above.
        mode = org_choices.get(org_choice, OrganizationMode.BOTH)

    console.print(f"✅ Selected: [green]{mode.value}[/green]")

    # Step 2: Categories
    console.print("\n[bold]Step 2: What expense categories should I use?[/bold]")
    cat_choices = {
        "1": CategoriesMode.AUTO,
        "2": CategoriesMode.BUSINESS,
        "3": CategoriesMode.PERSONAL
    }
    
    cat_choice = Prompt.ask(
        "Choose an option",
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

    # Save
    config = Config(
        organization_mode=mode,
        categories_mode=cat_mode,
        custom_categories=custom_cats
    )
    
    # Ensure system dir exists
    workspace.system.mkdir(parents=True, exist_ok=True)
    
    with open(workspace.config_path, "w") as f:
        yaml.dump(config.model_dump(), f)
        
    console.print(f"\n✨ Configuration saved to [bold]{workspace.config_path}[/bold]")
    console.print("You are ready to run: [bold green]coworker run[/bold]")
