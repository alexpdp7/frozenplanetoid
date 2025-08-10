# Frozen Planetoid

Frozen Planetoid can generate static sites that aggregate the content of multiple websites through their RSS feed.

For example, [this is a couple of tech blogs I follow](https://alexpdp7.github.io/frozenplanetoid/tech.html).

Because Frozen Planetoid generates static sites, you can host Frozen Planetoid with services such as GitHub Pages, or basic web hosting.

You can use Frozen Planetoid:

* ... as a low cost RSS feed reader
* ... to promote websites that provide good RSS feeds

## Usage

You can use `pipx` or `uv` to run the program without installing.

```
pipx run --spec git+https://github.com/alexpdp7/frozenplanetoid.git/ frozenplanetoid --help
```

```
uvx --with git+https://github.com/alexpdp7/frozenplanetoid.git/ frozenplanetoid --help
```
