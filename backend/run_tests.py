#!/usr/bin/env python3
"""
Test Runner pour Risk Management Backend
Lance tous les tests avec pytest
"""
import sys
import subprocess


def main():
    """
    Lance les tests pytest avec configuration optimale
    """
    print("=" * 60)
    print("🧪 Risk Management Backend - Test Suite")
    print("=" * 60)
    print()

    # Commande pytest
    cmd = [
        "pytest",
        "tests/",
        "-v",  # Verbose
        "--tb=short",  # Traceback court
        "--color=yes",  # Couleurs
    ]

    # Lancer pytest
    result = subprocess.run(cmd)

    # Retourner le code de sortie
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
