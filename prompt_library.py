"""
prompt_library.py
Store and manage common prompts for your MCP agent
"""

from typing import Dict, List, Optional
import json
from pathlib import Path


class PromptLibrary:
    """Manage a library of reusable prompts"""

    def __init__(self, library_file: str = "prompt_library.json"):
        self.library_file = Path(library_file)
        self.prompts = self._load_library()

    def _load_library(self) -> Dict:
        """Load prompts from file"""
        if self.library_file.exists():
            with open(self.library_file, 'r') as f:
                return json.load(f)
        return {"prompts": {}, "categories": {}}

    def _save_library(self):
        """Save prompts to file"""
        with open(self.library_file, 'w') as f:
            json.dump(self.prompts, f, indent=2)

    def add_prompt(
            self,
            name: str,
            template: str,
            category: str = "general",
            description: str = "",
            variables: List[str] = None
    ):
        """
        Add a new prompt template to the library

        Args:
            name: Unique name for this prompt
            template: The prompt text (can include {variables})
            category: Category for organization
            description: What this prompt does
            variables: List of variable names in the template
        """
        self.prompts["prompts"][name] = {
            "template": template,
            "category": category,
            "description": description,
            "variables": variables or []
        }

        # Track categories
        if category not in self.prompts["categories"]:
            self.prompts["categories"][category] = []
        if name not in self.prompts["categories"][category]:
            self.prompts["categories"][category].append(name)

        self._save_library()
        print(f"✅ Prompt '{name}' added to library")

    def get_prompt(self, name: str, **kwargs) -> Optional[str]:
        """
        Get a prompt by name and fill in variables

        Args:
            name: Name of the prompt
            **kwargs: Variables to fill in the template

        Returns:
            Formatted prompt string or None if not found
        """
        if name not in self.prompts["prompts"]:
            print(f"❌ Prompt '{name}' not found")
            return None

        prompt_data = self.prompts["prompts"][name]
        template = prompt_data["template"]

        try:
            return template.format(**kwargs)
        except KeyError as e:
            print(f"❌ Missing variable: {e}")
            print(f"Required variables: {prompt_data['variables']}")
            return None

    def list_prompts(self, category: Optional[str] = None):
        """List all prompts, optionally filtered by category"""
        if category:
            if category in self.prompts["categories"]:
                prompts = self.prompts["categories"][category]
            else:
                print(f"❌ Category '{category}' not found")
                return
        else:
            prompts = list(self.prompts["prompts"].keys())

        print(f"\n{'=' * 80}")
        print(f"PROMPTS{f' - Category: {category}' if category else ''}")
        print(f"{'=' * 80}\n")

        for prompt_name in prompts:
            prompt_data = self.prompts["prompts"][prompt_name]
            print(f"📝 {prompt_name}")
            print(f"   Category: {prompt_data['category']}")
            print(f"   Description: {prompt_data['description']}")
            if prompt_data['variables']:
                print(f"   Variables: {', '.join(prompt_data['variables'])}")
            print()

    def list_categories(self):
        """List all categories"""
        print("\n📚 Available Categories:")
        for category, prompts in self.prompts["categories"].items():
            print(f"  • {category} ({len(prompts)} prompts)")

    def search_prompts(self, keyword: str) -> List[str]:
        """Search prompts by keyword in name or description"""
        matches = []
        keyword_lower = keyword.lower()

        for name, data in self.prompts["prompts"].items():
            if (keyword_lower in name.lower() or
                    keyword_lower in data['description'].lower() or
                    keyword_lower in data['template'].lower()):
                matches.append(name)

        return matches

    def delete_prompt(self, name: str):
        """Delete a prompt from the library"""
        if name in self.prompts["prompts"]:
            category = self.prompts["prompts"][name]["category"]
            del self.prompts["prompts"][name]

            # Remove from category
            if category in self.prompts["categories"]:
                self.prompts["categories"][category].remove(name)

            self._save_library()
            print(f"✅ Prompt '{name}' deleted")
        else:
            print(f"❌ Prompt '{name}' not found")


# Example usage and preset prompts
def create_default_library():
    """Create a library with common economic analysis prompts"""

    library = PromptLibrary()

    # Inflation Analysis
    library.add_prompt(
        name="inflation_check",
        template="What's happening with inflation right now? Pull the latest CPI data from FRED and check recent economic news articles.",
        category="inflation",
        description="Quick inflation status check with data and news"
    )

    library.add_prompt(
        name="inflation_deep_dive",
        template="Analyze inflation trends over the past {months} months. Break down by major categories (food, energy, housing, services) and compare to the Fed's 2% target. What's driving current inflation?",
        category="inflation",
        description="Detailed inflation analysis with category breakdown",
        variables=["months"]
    )

    # Labor Market
    library.add_prompt(
        name="unemployment_trend",
        template="Analyze the unemployment trend over the past {period}. What do recent news articles say about the labor market?",
        category="labor",
        description="Unemployment trend analysis with news context",
        variables=["period"]
    )

    library.add_prompt(
        name="labor_market_snapshot",
        template="Give me a complete labor market snapshot: unemployment rate, job openings, wage growth, and labor force participation. How does this compare to pre-pandemic levels?",
        category="labor",
        description="Comprehensive labor market overview"
    )

    # Fed Policy
    library.add_prompt(
        name="fed_rate_outlook",
        template="Based on current trends and recent economic news, what's your outlook for interest rates over the next {timeframe}? Provide confidence level and key factors to watch.",
        category="fed_policy",
        description="Interest rate outlook with confidence assessment",
        variables=["timeframe"]
    )

    library.add_prompt(
        name="fed_announcements",
        template="What has the Federal Reserve announced recently? Only check official sources.",
        category="fed_policy",
        description="Recent Fed announcements from official sources only"
    )

    # Economic Snapshots
    library.add_prompt(
        name="economic_snapshot",
        template="Give me an economic snapshot: what's happening with GDP growth, inflation, and unemployment? Include both data and recent news.",
        category="snapshot",
        description="Quick overview of major economic indicators"
    )

    library.add_prompt(
        name="recession_risk",
        template="Should I be worried about a recession in {year}? Analyze leading indicators like yield curve, unemployment trends, consumer spending, and business investment.",
        category="snapshot",
        description="Recession risk assessment",
        variables=["year"]
    )

    # Sector-Specific
    library.add_prompt(
        name="housing_market",
        template="How is the housing market doing right now? Include home prices, sales volume, mortgage rates, and housing starts.",
        category="sectors",
        description="Housing market analysis"
    )

    library.add_prompt(
        name="sector_analysis",
        template="Analyze the current state of the {sector} sector. What are the trends, challenges, and outlook?",
        category="sectors",
        description="Analysis of specific economic sector",
        variables=["sector"]
    )

    # Comparisons
    library.add_prompt(
        name="historical_comparison",
        template="Compare current {indicator} to {comparison_period}. What's different and why does it matter?",
        category="comparison",
        description="Historical comparison of economic indicators",
        variables=["indicator", "comparison_period"]
    )

    library.add_prompt(
        name="inflation_drivers",
        template="What's driving inflation right now - supply issues or demand? Analyze both sides with evidence.",
        category="inflation",
        description="Supply vs demand analysis for inflation"
    )

    print("✅ Default prompt library created!")
    return library


# CLI Interface
def prompt_library_cli():
    """Interactive CLI for managing prompts"""
    library = PromptLibrary()

    while True:
        print("\n" + "=" * 80)
        print("PROMPT LIBRARY MANAGER")
        print("=" * 80)
        print("\nCommands:")
        print("  1. List all prompts")
        print("  2. List by category")
        print("  3. Get prompt")
        print("  4. Search prompts")
        print("  5. Add new prompt")
        print("  6. Delete prompt")
        print("  7. Exit")

        choice = input("\nEnter command number: ").strip()

        if choice == "1":
            library.list_prompts()

        elif choice == "2":
            library.list_categories()
            category = input("Enter category name: ").strip()
            library.list_prompts(category)

        elif choice == "3":
            name = input("Enter prompt name: ").strip()
            prompt_data = library.prompts["prompts"].get(name)

            if prompt_data:
                print(f"\n📝 {name}")
                print(f"Description: {prompt_data['description']}")
                print(f"Template: {prompt_data['template']}\n")

                if prompt_data['variables']:
                    print("Variables needed:")
                    kwargs = {}
                    for var in prompt_data['variables']:
                        value = input(f"  {var}: ").strip()
                        kwargs[var] = value

                    result = library.get_prompt(name, **kwargs)
                    if result:
                        print(f"\n✅ Formatted prompt:\n{result}")
                else:
                    print(f"✅ Prompt: {library.get_prompt(name)}")

        elif choice == "4":
            keyword = input("Enter search keyword: ").strip()
            matches = library.search_prompts(keyword)

            if matches:
                print(f"\n🔍 Found {len(matches)} matches:")
                for match in matches:
                    print(f"  • {match}")
            else:
                print("❌ No matches found")

        elif choice == "5":
            name = input("Prompt name: ").strip()
            template = input("Prompt template: ").strip()
            category = input("Category: ").strip()
            description = input("Description: ").strip()

            variables_input = input("Variables (comma-separated, or blank): ").strip()
            variables = [v.strip() for v in variables_input.split(",")] if variables_input else []

            library.add_prompt(name, template, category, description, variables)

        elif choice == "6":
            name = input("Enter prompt name to delete: ").strip()
            confirm = input(f"Delete '{name}'? (y/n): ").strip().lower()
            if confirm == 'y':
                library.delete_prompt(name)

        elif choice == "7":
            print("👋 Goodbye!")
            break

        else:
            print("❌ Invalid command")


if __name__ == "__main__":
    # First time setup
    import sys

    if "--setup" in sys.argv:
        print("Setting up default prompt library...")
        create_default_library()
    elif "--cli" in sys.argv:
        prompt_library_cli()
    else:
        print("\nUsage:")
        print("  python prompt_library.py --setup  # Create default library")
        print("  python prompt_library.py --cli    # Interactive manager")