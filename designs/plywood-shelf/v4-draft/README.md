# V4 molding and retainer draft — NOT EXECUTED

This directory preserves preliminary source written before access to the closet model was resolved. It is not a printable handoff and has no generated exports or successful test results.

Read [the progress handoff](../PROGRESS.md) first. Closet.zip is a 3D model and remains uninspected.

The source is isolated from the active V3 builder and does not trigger the current CAD workflow. Parameters in this directory belong only to the draft. Review the actual closet model before running or promoting them.

After that review, an appropriate CAD environment can execute:

```sh
python -m pip install -r designs/plywood-shelf/requirements.txt
python designs/plywood-shelf/v4-draft/build.py
```

The builder would write its own exports beneath this directory. Any passing receipt must result from a real successful run. It cannot be inferred from source review.
