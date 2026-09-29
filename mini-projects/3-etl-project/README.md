# FSB Bank E-Statement ETL Project

This project completes the two-part ETL assignment in [ETL PROJECT.pdf](ETL%20PROJECT.pdf). The goal is to inspect six source tables in an Excel workbook and build `f_estatement_trx`, a transaction datamart for an electronic bank statement.

## Project files

| File | Purpose |
| --- | --- |
| [FSB Bank Transaction.xlsx](FSB%20Bank%20Transaction.xlsx) | Source workbook with the transaction table and five master tables. |
| [part_one.ipynb](part_one.ipynb) | Part 1: source inspection, data dictionary, profiling, and quality checks. |
| [part_one_ERD.png](part_one_ERD.png) | ERD of the six source tables. |
| [part_two.ipynb](part_two.ipynb) | Part 2: extract, transform, validate, export, and load the datamart. |
| [part_two_data_flow.png](part_two_data_flow.png) | Data flow from Excel to the datamart and Excel output. |
| [f_estatement_trx.xlsx](f_estatement_trx.xlsx) | Exported datamart for comparison and submission. |

## Part 1: inspect the source

The workbook contains `transaction`, `master_account`, `master_customer`, `master_transaction_code`, `master_bank_code`, and `master_branch`. The notebook records their columns, pandas data types, row counts, missing values, duplicate rows, key uniqueness, and relationships. Its Markdown cells describe the fields and summarize the findings. The ERD shows the source-table relationships.

Main source issues found:

- 16 transaction rows reference an account absent from `master_account`.
- Bank code `116` appears with two different bank names.
- All 123 customer opening dates are later than their linked account opening dates.
- Four paired internal transfers have different debit and credit amounts.

## Part 2: build the datamart

The ETL reads all six Excel sheets with pandas, removes standalone monthly-fee rows, and attaches paired ATM and transfer fees to their main transaction in `additional_amount`. It joins the master tables, converts Julian transaction dates and integer transaction times, derives the statement transaction type, and parses counterparty details from transaction remarks.

The result has **1,202 rows and 29 columns**. It is saved as [f_estatement_trx.xlsx](f_estatement_trx.xlsx) and loaded into the PostgreSQL table `f_estatement_trx`. The final notebook cell reads back the table for verification.

Source exceptions remain visible in the output. For example, 14 output rows have no matching account master, and bank names are blank where a bank code is missing from the lookup or maps to more than one name. Review these records before using the table as production data.

## Run the notebooks

Use Python 3.11. From this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
jupyter notebook
```

Open `part_one.ipynb`, then `part_two.ipynb`, and run each notebook from top to bottom. Keep the source workbook in the same directory. In VS Code, select the `.venv` Python kernel.

The Part 2 load cell uses PostgreSQL at `localhost:5432`, database `db_mini_project_3_elt_project`, user `postgres`, and an empty password, as configured for this project. Start that database before running the load and verification cells. The load cell uses `if_exists='replace'`, so rerunning it replaces the current `f_estatement_trx` table.

## Submission

The mentor allows `part_one.ipynb` instead of a Part 1 PDF. Include its ERD image. For Part 2, submit the Excel output and the requested screenshots of the Python code and PostgreSQL table; the final notebook cells show the table result to capture.
