import json
import requests
import csv
from pprint import pprint
from prettytable import PrettyTable
from steem.amount import Amount
from steem.transactionbuilder import TransactionBuilder
from steembase.operations import Transfer
import argparse
from datetime import datetime, timedelta
import sys


def valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)


def query_yes_no(question, default="yes"):
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)
    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")


parser = argparse.ArgumentParser(
    description="Payout tool for Streemian guilds"
)

parser.add_argument(
    'guild',
    type=str,
    help='Guild'
)

parser.add_argument(
    '-s',
    "--startdate",
    default=(datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d"),
    help="The Start Date - format YYYY-MM-DD ",
    type=valid_date
)

parser.add_argument(
    '-e',
    "--enddate",
    default=datetime.utcnow().strftime("%Y-%m-%d"),
    help="The End Date format YYYY-MM-DD",
    type=valid_date
)

parser.add_argument(
    'authtoken',
    type=str,
    help='Authentication token (obtainable from the profile)'
)

parser.add_argument(
    '-a',
    '--account',
    type=str,
    default="curie",
    help='Send amounts from this account'
)

parser.add_argument(
    '-p',
    '--proposerfee',
    type=str,
    default="0.05 SBD",
    help='Proposer fee'
)

parser.add_argument(
    '-r',
    '--reviewerfee',
    type=str,
    default="0.05 SBD",
    help='Reviewer fee'
)

args = parser.parse_args()
tx = TransactionBuilder()
proposer_base_reward = Amount(args.proposerfee)
reviewer_base_reward = Amount(args.reviewerfee)

r = requests.post(
    'https://streemian.com/api/guild/curie/admin/accounting/{start}/{end}/curator'.format(
        start=args.startdate.strftime("%Y-%m-%d"),
        end=args.enddate.strftime("%Y-%m-%d")
    ),
    headers={'Authentication-Token': args.authtoken}
)
curators = r.json()

r = requests.post(
    'https://streemian.com/api/guild/curie/admin/accounting/{start}/{end}/reviewer'.format(
        start=args.startdate.strftime("%Y-%m-%d"),
        end=args.enddate.strftime("%Y-%m-%d")
    ),
    headers={'Authentication-Token': args.authtoken}
)
reviewers = r.json()

t_curators = PrettyTable(["Proposer", "nr. accepted"])
for curator in curators:
    if not int(curator["num_accepted"]):
        continue
    tx.appendOps(Transfer(
        **{"from": args.account,
           "to": curator["proposer"],
           "amount": str(proposer_base_reward * int(curator["num_accepted"])),
           "memo": "Finder's Fee"
           }
    ))
    t_curators.add_row([curator["proposer"], curator["num_accepted"]])

t_reviewers = PrettyTable(["Reviewer", "nr. accepted"])
for reviewer in reviewers:
    if not int(reviewer["num_reviews"]):
        continue
    tx.appendOps(Transfer(
        **{"from": args.account,
           "to": reviewer["reviewer"],
           "amount": str(proposer_base_reward * int(reviewer["num_reviews"])),
           "memo": "Reviewer's Fee"
           }
    ))
    t_reviewers.add_row([reviewer["reviewer"], reviewer["num_reviews"]])

print(t_reviewers)
print()
print(t_curators)

tx.appendSigner(args.account, "active")
pprint(tx.json())

if query_yes_no("Please confirm the transfer"):
    tx.broadcast()
