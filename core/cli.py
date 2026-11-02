"""Argument validation shared by generation and evaluation commands."""

import argparse


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("Value must be a positive integer")
    return number
