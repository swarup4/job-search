"""Evaluation of the scoring pipeline against a labelled set. (EV-03)

`dataset` is the labelled set's shape, `metrics` the arithmetic, `runner` the thing
that reads postings with the configured model and writes a report. Nothing here
reaches the API server: the pipeline's pure functions are called directly, so an
evaluation needs a model and a folder of labels, not an account.
"""
