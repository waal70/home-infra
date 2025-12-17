# How to contribute

This repository is pretty tailor-made for my own environment. However, I am very keen to learn your observations and/or fixes.
All changes are therefore welcomed!

Chances are, my blog will detail some of the intricacies here, so please drop by on https://waal70.org

## Submitting changes

Please send a Github Pull Request with a clear list of what you've done. And make sure all of your commits are atomic (one feature per commit).
Always write a clear log message for your commits. 

## Coding conventions

* Really just run ansible-lint on the production profile. This will tell you whether you are coding properly :)
* Commit messages should contain one of these prefixes, followed by a colon:

```yaml
[
  'build',
  'chore',
  'ci',
  'docs',
  'feat',
  'fix',
  'perf',
  'refactor',
  'revert',
  'style',
  'test'
];
```
