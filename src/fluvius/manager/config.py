"""Fluvius Configuration CLI commands."""

import click
import json
from typing import Any, Dict

from .entrypoint import fluvius_manager
from fluvius.helper import load_string

@fluvius_manager.command(name="config")
@click.argument('module_path', type=str, default='fluvius')
@click.option('--key', help='Specific config key to display (e.g., DB_DSN)')
@click.option('--format', 'output_format', 
              type=click.Choice(['table', 'json', 'yaml']), 
              default='table',
              help='Output format for config values')
@click.option('--filter', 'filter_pattern', 
              help='Filter config keys by pattern (case-insensitive)')
@click.option('--show-sensitive', is_flag=True, 
              help='Show sensitive values (passwords, tokens, etc.)')
@click.option('--show-source', is_flag=True,
              help='Show configuration source information (requires fluvius debug info)')
def show_config(module_path, key, output_format, filter_pattern, show_sensitive, show_source):
    """Display configuration values of an module"""
    config = load_string(f"{module_path}.config")

    try:
        # Get all config attributes using fluvius config methods
        config_data = {}
        sensitive_keys = ['password', 'pass', 'token', 'secret', 'key', 'dsn']
        
        # Get debug information from fluvius config
        vdebug = getattr(config, '__vdebug__', {})
        
        # Use fluvius config.items() method to get all configuration values
        for attr_name, attr_value in config.items():
            # Check if this is a sensitive value
            is_sensitive = any(sensitive_word in attr_name.lower() for sensitive_word in sensitive_keys)
            
            # Mask sensitive values unless explicitly requested
            if is_sensitive and not show_sensitive:
                if isinstance(attr_value, str) and len(attr_value) > 8:
                    attr_value = attr_value[:4] + '*' * (len(attr_value) - 8) + attr_value[-4:]
                else:
                    attr_value = '***'
            
            # Get debug info for this key if available
            debug_info = vdebug.get(attr_name, (attr_value, type(attr_value), 'unknown'))
            source_info = debug_info[2] if len(debug_info) > 2 else 'unknown'
            
            # Extract namespace (module name) - get it from config object
            namespace = getattr(config, '__name__', 'fluvius')
            
            # Format source info for display
            if isinstance(source_info, (list, tuple)):
                sourceinfo = source_info[0] if source_info else 'unknown'
            elif isinstance(source_info, str):
                sourceinfo = source_info
            else:
                sourceinfo = 'unknown'
            
            config_data[attr_name] = {
                'value': attr_value,
                'namespace': namespace,
                'sourceinfo': sourceinfo,
                'type': type(attr_value).__name__,
                'source': source_info if show_source else None
            }
        
        # Filter by specific key if requested
        if key:
            if key in config_data:
                config_data = {key: config_data[key]}
            else:
                click.echo(f"❌ Config key '{key}' not found")
                available_keys = ', '.join(sorted(config_data.keys()))
                click.echo(f"Available keys: {available_keys}")
                return
        
        # Filter by pattern if requested
        if filter_pattern:
            pattern = filter_pattern.lower()
            config_data = {
                k: v for k, v in config_data.items() 
                if pattern in k.lower()
            }
        
        if not config_data:
            click.echo("No configuration values found matching criteria")
            return
        
        # Output in requested format
        if output_format == 'json':
            if show_source:
                # Include full metadata for JSON when source is requested
                json_output = config_data
            else:
                # For JSON output, flatten the structure
                json_output = {k: v['value'] for k, v in config_data.items()}
            click.echo(json.dumps(json_output, indent=2, default=str))
        elif output_format == 'yaml':
            try:
                import yaml
                if show_source:
                    # Include full metadata for YAML when source is requested
                    yaml_output = config_data
                else:
                    # For YAML output, flatten the structure
                    yaml_output = {k: v['value'] for k, v in config_data.items()}
                click.echo(yaml.dump(yaml_output, default_flow_style=False))
            except ImportError:
                click.echo("❌ PyYAML not installed. Using JSON format instead.")
                if show_source:
                    json_output = config_data
                else:
                    json_output = {k: v['value'] for k, v in config_data.items()}
                click.echo(json.dumps(json_output, indent=2, default=str))
        else:  # table format (default)
            _print_config_table(config_data, show_sensitive, show_source)
            
    except Exception as e:
        click.echo(f"❌ Error retrieving configuration: {e}")


def _print_config_table(config_data: Dict[str, Dict[str, Any]], show_sensitive: bool, show_source: bool = False):
    """Print configuration in a formatted table."""
    
    if not config_data:
        click.echo("No configuration values to display")
        return
    
    # Calculate column widths
    max_key_width = max(len(key) for key in config_data.keys())
    max_value_width = max(len(str(data['value'])) for data in config_data.values())
    max_namespace_width = max(len(str(data['namespace'])) for data in config_data.values())
    max_sourceinfo_width = max(len(str(data['sourceinfo'])) for data in config_data.values())
    
    # Minimum and maximum column widths
    key_width = max(15, min(max_key_width, 36))
    value_width = max(20, min(max_value_width, 50))
    namespace_width = max(10, min(max_namespace_width, 32))
    sourceinfo_width = max(10, min(max_sourceinfo_width, 40))
    type_width = 8
    
    # Add source column if requested
    source_width = 0
    if show_source:
        max_source_width = max(len(str(data.get('source', ''))) for data in config_data.values())
        source_width = max(15, min(max_source_width, 30))
    
    # Calculate total width
    total_width = key_width + value_width + namespace_width + sourceinfo_width + type_width + 16  # 16 for separators
    if show_source:
        total_width += source_width + 3  # 3 for additional separator
    
    # Print header
    click.echo("🔧 Fluvius Configuration (from fluvius config system)")
    click.echo("=" * total_width)
    
    if show_source:
        click.echo(f"{'Key':<{key_width}} | {'Value':<{value_width}} | {'Namespace':<{namespace_width}} | {'Source Info':<{sourceinfo_width}} | {'Type':<{type_width}} | {'Source':<{source_width}}")
    else:
        click.echo(f"{'Key':<{key_width}} | {'Value':<{value_width}} | {'Namespace':<{namespace_width}} | {'Source Info':<{sourceinfo_width}} | {'Type':<{type_width}}")
    
    click.echo("-" * total_width)
    
    # Print config values
    for key, data in sorted(config_data.items()):
        # Truncate long values
        str_value = str(data['value'])
        if len(str_value) > value_width:
            str_value = str_value[:value_width-3] + "..."
        
        # Truncate long namespaces
        namespace = str(data['namespace'])
        if len(namespace) > namespace_width:
            namespace = namespace[:namespace_width-3] + "..."
        
        # Truncate long sourceinfo
        sourceinfo = str(data['sourceinfo'])
        if len(sourceinfo) > sourceinfo_width:
            sourceinfo = sourceinfo[:sourceinfo_width-3] + "..."
        
        value_type = data['type']
        
        if show_source:
            # Format source information
            source = str(data.get('source', 'unknown'))
            if len(source) > source_width:
                source = source[:source_width-3] + "..."
            
            click.echo(f"{key:<{key_width}} | {str_value:<{value_width}} | {namespace:<{namespace_width}} | {sourceinfo:<{sourceinfo_width}} | {value_type:<{type_width}} | {source:<{source_width}}")
        else:
            click.echo(f"{key:<{key_width}} | {str_value:<{value_width}} | {namespace:<{namespace_width}} | {sourceinfo:<{sourceinfo_width}} | {value_type:<{type_width}}")
    
    click.echo("=" * total_width)
    
    # Show legend
    if not show_sensitive:
        click.echo("\n💡 Tip: Use --show-sensitive to reveal masked values")
    
    if not show_source:
        click.echo("   Use --show-source to see configuration source details")
    
    click.echo("   Use --key <name> to show a specific configuration value")
    click.echo("   Configuration follows fluvius hierarchy: INI files > module defaults > system defaults")


