# Team related utilities
Utilities which are helpful for team processes

## Scripts

### `picker.py`

Given a list of options, this script will randomly select items one at a time without replacement.
You can pass in the options as arguments or pass in a path to a file containing the options, one per line.

Requires the `click` package. Can be run with `uv run` to automatically ensure dependencies are available.

```sh
uv run picker.py --help
uv run picker.py apple banana cherry
uv run picker.py -f ~/path/to/options.txt
```
