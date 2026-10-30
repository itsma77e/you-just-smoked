from you_just_smoked.cli import main

# Guarded: the camera helper process re-imports the main module when it starts.
if __name__ == "__main__":
    raise SystemExit(main())
