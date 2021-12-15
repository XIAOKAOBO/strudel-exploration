# Strudel - Exploration

This is the research on extension of the original strudel algorithm: https://github.com/lanchiang/strudel based on the paper https://edbt2021proceedings.github.io/docs/p32.pdf.

It did some exploration such as feature enrichments and column classifications

## Getting Started

### Executing program

* Use the following script to run the Strudel program:
```
python run_strudel.py
```
The following arguments can be used for the above script:
* -d: training dataset
* -t: test dataset. If not given, the program does cross-validation on the training dataset
* -f: dataset path
* -o: output path

* Results are stored in a csv file.

## Version History

* 0.1
    * Initial Release

## License

This project is licensed under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) License - see the LICENSE.md file for details




