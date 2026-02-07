"""
Format converter for exporting scraping results to multiple formats.
Supports: CSV, XLSX, Parquet, and SQL.
"""

import boto3
import json
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from io import BytesIO
from typing import Dict, List, Optional
from logger import get_logger

logger = get_logger(__name__)
s3_client = boto3.client('s3')


class FormatConverter:
    """Converts job results from JSON to various export formats."""

    def __init__(self, job_id: str, results_data: List[Dict], s3_bucket: str):
        """
        Initialize the format converter.

        Args:
            job_id: The job identifier
            results_data: List of result dictionaries from JSON
            s3_bucket: S3 bucket name for storing converted files
        """
        self.job_id = job_id
        self.results_data = results_data
        self.s3_bucket = s3_bucket
        self.df = None

    def prepare_dataframe(self, flatten: bool = False) -> pd.DataFrame:
        """
        Convert JSON results to Pandas DataFrame.

        Args:
            flatten: If True, flatten nested query results into columns

        Returns:
            Pandas DataFrame with results
        """
        if not self.results_data:
            logger.warning("No results data to convert", job_id=self.job_id)
            self.df = pd.DataFrame()
            return self.df

        if flatten:
            # Flatten nested query results into separate columns
            flattened = []
            for row in self.results_data:
                flat_row = {
                    'url': row.get('url', ''),
                    'status': row.get('status', ''),
                    'http_code': row.get('http_code', '')
                }

                # Add query results as individual columns
                data = row.get('data', {})
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, list):
                            # Join list values with pipe delimiter
                            flat_row[key] = '|'.join(str(v) for v in value)
                        else:
                            flat_row[key] = value

                flattened.append(flat_row)

            self.df = pd.DataFrame(flattened)
        else:
            # Keep nested structure
            self.df = pd.DataFrame(self.results_data)

        logger.info("DataFrame prepared", job_id=self.job_id, rows=len(self.df), flatten=flatten)
        return self.df

    def convert_to_csv(self, s3_key: str) -> str:
        """
        Convert to CSV and upload to S3.

        Args:
            s3_key: S3 key for the CSV file

        Returns:
            S3 key of uploaded file
        """
        if self.df is None:
            self.prepare_dataframe(flatten=True)

        # Convert to CSV with proper encoding
        csv_buffer = self.df.to_csv(index=False, encoding='utf-8')

        # Upload to S3
        s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=s3_key,
            Body=csv_buffer.encode('utf-8'),
            ContentType='text/csv',
            Metadata={
                'job-id': self.job_id,
                'format': 'csv',
                'row-count': str(len(self.df))
            }
        )

        logger.info("CSV file uploaded to S3", job_id=self.job_id, s3_key=s3_key, rows=len(self.df))
        return s3_key

    def convert_to_xlsx(self, s3_key: str) -> str:
        """
        Convert to Excel (XLSX) with formatting and upload to S3.

        Args:
            s3_key: S3 key for the XLSX file

        Returns:
            S3 key of uploaded file
        """
        if self.df is None:
            self.prepare_dataframe(flatten=True)

        # Create workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Job {self.job_id[:8]}"

        # Define header styling
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True, size=11)
        header_alignment = Alignment(horizontal="center", vertical="center")

        # Add headers with styling
        for col_idx, column in enumerate(self.df.columns, 1):
            cell = ws.cell(row=1, column=col_idx, value=column)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment

        # Add data rows
        for row_idx, row in enumerate(self.df.itertuples(index=False), 2):
            for col_idx, value in enumerate(row, 1):
                # Handle None and NaN values
                if pd.isna(value):
                    value = ''
                ws.cell(row=row_idx, column=col_idx, value=value)

        # Auto-size columns (with max width limit)
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter

            for cell in column:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass

            adjusted_width = min(max_length + 2, 50)  # Max width of 50
            ws.column_dimensions[column_letter].width = adjusted_width

        # Add auto-filter
        ws.auto_filter.ref = ws.dimensions

        # Freeze top row (headers)
        ws.freeze_panes = "A2"

        # Save to bytes buffer
        excel_buffer = BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)

        # Upload to S3
        s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=s3_key,
            Body=excel_buffer.getvalue(),
            ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            Metadata={
                'job-id': self.job_id,
                'format': 'xlsx',
                'row-count': str(len(self.df))
            }
        )

        logger.info("XLSX file uploaded to S3", job_id=self.job_id, s3_key=s3_key, rows=len(self.df))
        return s3_key

    def convert_to_parquet(self, s3_key: str) -> str:
        """
        Convert to Parquet with compression and upload to S3.

        Args:
            s3_key: S3 key for the Parquet file

        Returns:
            S3 key of uploaded file
        """
        if self.df is None:
            self.prepare_dataframe(flatten=True)

        # Convert to Parquet with Snappy compression
        parquet_buffer = BytesIO()
        self.df.to_parquet(parquet_buffer, compression='snappy', index=False, engine='pyarrow')
        parquet_buffer.seek(0)

        # Upload to S3
        s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=s3_key,
            Body=parquet_buffer.getvalue(),
            ContentType='application/octet-stream',
            Metadata={
                'job-id': self.job_id,
                'format': 'parquet',
                'row-count': str(len(self.df)),
                'compression': 'snappy'
            }
        )

        logger.info("Parquet file uploaded to S3", job_id=self.job_id, s3_key=s3_key, rows=len(self.df))
        return s3_key

    def convert_to_sql(self, s3_key: str, table_name: str = 'scraped_data') -> str:
        """
        Generate SQL INSERT statements and upload to S3.

        Args:
            s3_key: S3 key for the SQL file
            table_name: Name of the SQL table

        Returns:
            S3 key of uploaded file
        """
        if self.df is None:
            self.prepare_dataframe(flatten=True)

        sql_statements = []

        # Create table statement with TEXT columns
        columns = ', '.join([f"`{col}` TEXT" for col in self.df.columns])
        create_table = f"CREATE TABLE IF NOT EXISTS `{table_name}` ({columns});\n\n"
        sql_statements.append(create_table)

        # Generate INSERT statements in batches of 100 rows
        batch_size = 100
        for i in range(0, len(self.df), batch_size):
            batch = self.df.iloc[i:i+batch_size]
            values = []

            for row in batch.itertuples(index=False):
                # Escape values and handle None
                escaped = []
                for v in row:
                    if pd.isna(v) or v is None:
                        escaped.append('NULL')
                    else:
                        # Escape single quotes by doubling them
                        escaped_value = str(v).replace("'", "''")
                        escaped.append(f"'{escaped_value}'")

                values.append(f"({', '.join(escaped)})")

            # Create INSERT statement
            insert_stmt = f"INSERT INTO `{table_name}` ({', '.join([f'`{col}`' for col in self.df.columns])}) VALUES\n"
            insert_stmt += ',\n'.join(values) + ";\n\n"
            sql_statements.append(insert_stmt)

        sql_content = ''.join(sql_statements)

        # Upload to S3
        s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=s3_key,
            Body=sql_content.encode('utf-8'),
            ContentType='application/sql',
            Metadata={
                'job-id': self.job_id,
                'format': 'sql',
                'table-name': table_name,
                'row-count': str(len(self.df))
            }
        )

        logger.info("SQL file uploaded to S3", job_id=self.job_id, s3_key=s3_key,
                   table_name=table_name, rows=len(self.df))
        return s3_key
