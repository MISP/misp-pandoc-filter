**This is a work in progress!** Very interested in suggestions for improvements or features, as well as any bugs.

The purpose of this filter is to convert a MISP markdown-based event report to a PDF via pandoc. It allows you to use MISP reports in your typical pandoc flow, which may include customized templates, styles, additional filters, etc. In addition to converting MISP IDs in an event report to attributes, objects, and tags, it also adds an appendix containing all objects and attributes in a given event.

This filter is written in pure python; there are no additional dependencies to install.

To work, all files need to be copied into a directory with the `event.json` downloaded MISP file. 

Example command: 
```
pandoc INPUT_MARKDOWN_FILE -o OUTPUT_PDF_FILE --filter ./misp-parser.py --include-in-header style.tex
```

To Do: 
- MISP API connection
