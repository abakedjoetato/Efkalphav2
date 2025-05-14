#!/usr/bin/env python3
"""
py-cord Compatibility Verification Tool

This script checks the installed Discord library for compatibility with the bot
and provides detailed diagnostics about potential issues.

Usage:
    python verify_compatibility.py [--fix] [--verbose]
"""

import argparse
import importlib
import inspect
import logging
import os
import sys
import traceback
from typing import Dict, List, Optional, Set, Tuple, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("compatibility_check")

# Import compatibility layer
try:
    from utils.discord_compat import discord, commands, is_pycord, is_pycord_261, discord_version
except ImportError:
    logger.error("Could not import discord_compat module. Make sure it exists in utils/")
    sys.exit(1)


class CompatibilityChecker:
    """Tool to check Discord library compatibility issues"""
    
    def __init__(self, args):
        self.fix = args.fix
        self.verbose = args.verbose
        
        if self.verbose:
            logger.setLevel(logging.DEBUG)
        
        # Results
        self.issues = []
        self.fixes_applied = []
    
    def check_discord_version(self) -> bool:
        """Check Discord library version"""
        logger.info(f"Checking Discord library version: {discord_version}")
        
        # Check if using py-cord
        if not is_pycord:
            self.issues.append(("Critical", "Not using py-cord", 
                               "The bot is designed to work with py-cord, but a different Discord library was detected."))
            logger.error("Not using py-cord. Please install py-cord: pip install py-cord==2.6.1")
            return False
        
        # Check for py-cord 2.6.1 specifically
        if not is_pycord_261:
            self.issues.append(("Warning", "Not using py-cord 2.6.1", 
                               f"The bot is designed for py-cord 2.6.1, but version {discord_version} was detected."))
            logger.warning(f"Using py-cord {discord_version}, but 2.6.1 is recommended.")
        
        return True
    
    def check_slash_command_group(self) -> bool:
        """Check SlashCommandGroup functionality"""
        logger.info("Checking SlashCommandGroup functionality")
        
        try:
            # Create a test SlashCommandGroup
            test_group = discord.SlashCommandGroup(name="test", description="Test group")
            
            # Check for command method
            if not hasattr(test_group, "command"):
                self.issues.append(("Critical", "SlashCommandGroup missing command method", 
                                  "The SlashCommandGroup class does not have a command method, which is required."))
                logger.error("SlashCommandGroup does not have command method")
                return False
            
            # Try to create a sub-command
            try:
                @test_group.command(name="subcommand", description="Test subcommand")
                async def test_subcommand(self, ctx):
                    pass
                
                logger.debug("Successfully created a subcommand with SlashCommandGroup")
            except Exception as e:
                self.issues.append(("Critical", "SlashCommandGroup command method error", 
                                  f"Could not create a subcommand: {str(e)}"))
                logger.error(f"Error using SlashCommandGroup.command(): {e}")
                return False
            
            return True
        except Exception as e:
            self.issues.append(("Critical", "SlashCommandGroup test failed", 
                              f"Could not test SlashCommandGroup: {str(e)}"))
            logger.error(f"Error testing SlashCommandGroup: {e}")
            return False
    
    def check_option_syntax(self) -> bool:
        """Check Option syntax for slash commands"""
        logger.info("Checking Option syntax")
        
        try:
            # Try to create an Option
            test_option = discord.Option(str, "Test option", required=True)
            
            # Check required attributes
            if not hasattr(test_option, "required"):
                self.issues.append(("Warning", "Option missing required attribute", 
                                  "The Option class does not have a required attribute."))
                logger.warning("Option class does not have required attribute")
            
            return True
        except Exception as e:
            self.issues.append(("Critical", "Option class test failed", 
                              f"Could not test Option class: {str(e)}"))
            logger.error(f"Error testing Option class: {e}")
            return False
    
    def check_interaction_handling(self) -> bool:
        """Check interaction handling capabilities"""
        logger.info("Checking interaction handling")
        
        try:
            # Check for ApplicationContext
            app_context_exists = hasattr(discord, "ApplicationContext")
            
            if not app_context_exists:
                self.issues.append(("Warning", "ApplicationContext not found", 
                                  "The ApplicationContext class is not available, which may cause issues."))
                logger.warning("ApplicationContext class not found")
            
            # Check Interaction class
            if not hasattr(discord, "Interaction"):
                self.issues.append(("Critical", "Interaction class not found", 
                                  "The Interaction class is not available, which will cause issues."))
                logger.error("Interaction class not found")
                return False
            
            # Check response methods
            interaction_class = discord.Interaction
            interaction_methods = dir(interaction_class)
            
            if "response" not in interaction_methods and not app_context_exists:
                self.issues.append(("Critical", "Interaction.response not found", 
                                  "The Interaction class does not have a response attribute, which will cause issues."))
                logger.error("Interaction.response not found")
                return False
            
            return True
        except Exception as e:
            self.issues.append(("Critical", "Interaction handling test failed", 
                              f"Could not test interaction handling: {str(e)}"))
            logger.error(f"Error testing interaction handling: {e}")
            return False
    
    def check_compatibility_files(self) -> bool:
        """Check for required compatibility files"""
        logger.info("Checking for compatibility files")
        
        required_files = [
            "utils/discord_compat.py",
            "utils/interaction_handlers.py",
            "utils/safe_mongodb_compat.py"
        ]
        
        missing_files = []
        
        for file_path in required_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            self.issues.append(("Critical", "Missing compatibility files", 
                              f"The following compatibility files are missing: {', '.join(missing_files)}"))
            logger.error(f"Missing compatibility files: {', '.join(missing_files)}")
            return False
        
        return True
    
    def get_all_cogs(self) -> List[str]:
        """Get all cog files in the cogs directory"""
        try:
            cog_dir = "cogs"
            cog_files = []
            
            # Check if cogs directory exists
            if not os.path.exists(cog_dir) or not os.path.isdir(cog_dir):
                logger.warning("cogs directory not found")
                return []
            
            # Find all Python files in cogs directory
            for file in os.listdir(cog_dir):
                if file.endswith(".py") and not file.startswith("_"):
                    cog_files.append(os.path.join(cog_dir, file))
            
            return cog_files
        except Exception as e:
            logger.error(f"Error getting cog files: {e}")
            return []
    
    def check_cog_compatibility(self) -> bool:
        """Check cogs for compatibility issues"""
        logger.info("Checking cogs for compatibility issues")
        
        cog_files = self.get_all_cogs()
        
        if not cog_files:
            self.issues.append(("Warning", "No cog files found", 
                              "Could not find any cog files to check."))
            logger.warning("No cog files found")
            return True  # Not a critical error
        
        # Check each cog file for compatibility issues
        cog_issues = 0
        
        for cog_file in cog_files:
            try:
                with open(cog_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Check for common compatibility issues
                issues_in_file = []
                
                # Check for SlashCommandGroup issues
                if "@bounty.command" in content and "SlashCommandGroup" not in content:
                    issues_in_file.append("Uses @group.command() but doesn't define SlashCommandGroup")
                
                # Check for option decorator issues
                if "@option" in content:
                    issues_in_file.append("Uses @option decorator which may not work in py-cord 2.6.1")
                
                # Check for describe decorator issues
                if "@describe" in content:
                    issues_in_file.append("Uses @describe decorator which may not work in py-cord 2.6.1")
                
                # Check for Application Context references
                if "ApplicationContext" not in content and "ctx.respond" in content:
                    issues_in_file.append("Uses ctx.respond but doesn't reference ApplicationContext")
                
                # Check for direct interaction assumptions
                if "interaction.response" in content and "hasattr(interaction, 'response')" not in content:
                    issues_in_file.append("Directly uses interaction.response without checking if it exists")
                
                # Log issues
                if issues_in_file:
                    cog_name = os.path.basename(cog_file)
                    self.issues.append(("Warning", f"Compatibility issues in {cog_name}", 
                                      f"The following issues were found: {', '.join(issues_in_file)}"))
                    logger.warning(f"Compatibility issues in {cog_name}: {', '.join(issues_in_file)}")
                    cog_issues += 1
                else:
                    logger.debug(f"No compatibility issues found in {os.path.basename(cog_file)}")
            
            except Exception as e:
                logger.error(f"Error checking cog {cog_file}: {e}")
                cog_issues += 1
        
        if cog_issues > 0:
            logger.warning(f"Found compatibility issues in {cog_issues} cog files")
        else:
            logger.info("No compatibility issues found in cog files")
        
        return True  # Not a critical error
    
    def check_all(self) -> bool:
        """Run all compatibility checks"""
        logger.info("Starting compatibility checks")
        
        # Run checks
        discord_version_ok = self.check_discord_version()
        slash_group_ok = self.check_slash_command_group()
        option_syntax_ok = self.check_option_syntax()
        interaction_ok = self.check_interaction_handling()
        files_ok = self.check_compatibility_files()
        cogs_ok = self.check_cog_compatibility()
        
        # Determine overall result
        critical_issues = [issue for issue in self.issues if issue[0] == "Critical"]
        warning_issues = [issue for issue in self.issues if issue[0] == "Warning"]
        
        logger.info(f"Compatibility check completed with {len(critical_issues)} critical issues and {len(warning_issues)} warnings")
        
        return len(critical_issues) == 0
    
    def print_report(self) -> None:
        """Print a report of compatibility issues"""
        print("\n=== COMPATIBILITY REPORT ===\n")
        
        if not self.issues:
            print("No compatibility issues found. The bot should work correctly.")
            return
        
        # Print critical issues first
        critical_issues = [issue for issue in self.issues if issue[0] == "Critical"]
        if critical_issues:
            print("CRITICAL ISSUES:")
            for i, (_, title, description) in enumerate(critical_issues, 1):
                print(f"{i}. {title}")
                print(f"   {description}")
                print()
        
        # Then print warnings
        warning_issues = [issue for issue in self.issues if issue[0] == "Warning"]
        if warning_issues:
            print("WARNINGS:")
            for i, (_, title, description) in enumerate(warning_issues, 1):
                print(f"{i}. {title}")
                print(f"   {description}")
                print()
        
        # Print fixes applied
        if self.fixes_applied:
            print("FIXES APPLIED:")
            for i, fix in enumerate(self.fixes_applied, 1):
                print(f"{i}. {fix}")
            print()
        
        # Print recommendation
        if critical_issues:
            print("RECOMMENDATION: Fix the critical issues before running the bot.")
        elif warning_issues:
            print("RECOMMENDATION: The bot may work, but consider addressing the warnings.")
        else:
            print("RECOMMENDATION: The bot should work correctly.")
        
        print("\n=== END OF REPORT ===")


def main():
    parser = argparse.ArgumentParser(
        description="Check for Discord library compatibility issues"
    )
    parser.add_argument(
        "--fix", 
        action="store_true", 
        help="Attempt to fix compatibility issues"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    checker = CompatibilityChecker(args)
    
    # Run checks
    all_ok = checker.check_all()
    
    # Print report
    checker.print_report()
    
    # Return exit code
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()