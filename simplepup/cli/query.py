import click
import json
import logging
import paramiko.ssh_exception
import requests
import socket
import sys

import simplepup.puppetdb as puppetdb

def set_up_logging(level=logging.WARNING):
    logging.captureWarnings(True)

    handler = logging.StreamHandler(stream=sys.stdout)
    try:
        import colorlog
        handler.setFormatter(colorlog.ColoredFormatter(
            "%(log_color)s%(name)s[%(processName)s]: %(message)s"))
    except ImportError:
        handler.setFormatter(logging.Formatter("%(name)s[%(processName)s]: %(message)s"))

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)

    logging.getLogger("paramiko").setLevel(logging.FATAL)

def main():
    try:
        cli(standalone_mode=False)
    except click.ClickException as e:
        e.show()
        sys.exit(e.exit_code)
    except click.Abort as e:
        sys.exit(e)

@click.command()
@click.option("--host", "-h", default="localhost",
    help="PuppetDB host to query")
@click.option("--limit", "-l", type=int,
    help="Maximum number of results to return")
@click.option("--sort", "-s", help="Attribute to sort by")
@click.option("--all", "-A", default=False, is_flag=True,
    help="Include expired and deactivated nodes")
@click.option("--verbose", "-v", default=False, is_flag=True)
@click.option("--debug", "-d", default=False, is_flag=True)
@click.argument("query", required=True)
@click.version_option()
def cli(host, limit, sort, all, verbose, debug, query):
    """Query PuppetDB with PQL"""

    if debug:
        set_up_logging(logging.DEBUG)
    elif verbose:
        set_up_logging(logging.INFO)
    else:
        set_up_logging(logging.WARNING)

    filter = puppetdb.QueryFilter()
    if not all:
        filter.add("nodes { deactivated is null and expired is null }")

    try:
        with puppetdb.AutomaticConnection(host) as pdb:
            results = pdb.query(filter(query), limit=limit, order_by=sort)
            print(json.dumps(results, indent=2, sort_keys=True))
    except socket.gaierror as e:
        sys.exit("PuppetDB connection (Socket): {}".format(e))
    except paramiko.ssh_exception.SSHException as e:
        sys.exit("PuppetDB connection (SSH): {}".format(e))
    except puppetdb.ResponseError as e:
        sys.exit(e)
    except puppetdb.QueryError as e:
        sys.exit(e)
    except requests.exceptions.ConnectionError as e:
        sys.exit(e)

