"""Table locations and the Spark session, configured for local disk or S3-compatible storage."""

from __future__ import annotations

import os
from dataclasses import dataclass

from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession

HADOOP_AWS = "org.apache.hadoop:hadoop-aws:3.3.4"


@dataclass(frozen=True)
class Tables:
    root: str

    @property
    def bronze_trips(self) -> str:
        return f"{self.root}/bronze/yellow_trips"

    @property
    def bronze_zones(self) -> str:
        return f"{self.root}/bronze/taxi_zones"

    @property
    def silver_trips(self) -> str:
        return f"{self.root}/silver/trips"

    @property
    def silver_rejected(self) -> str:
        return f"{self.root}/silver/trips_rejected"

    @property
    def gold_daily_zone_demand(self) -> str:
        return f"{self.root}/gold/daily_zone_demand"

    @property
    def gold_hourly_demand(self) -> str:
        return f"{self.root}/gold/hourly_demand"

    @property
    def gold_daily_kpis(self) -> str:
        return f"{self.root}/gold/daily_kpis"


def tables_from_env() -> Tables:
    return Tables(root=os.getenv("LAKEHOUSE_ROOT", "data/lakehouse").rstrip("/"))


def build_spark(app_name: str = "lakehouse", root: str | None = None) -> SparkSession:
    root = root or tables_from_env().root
    builder = (
        SparkSession.builder.appName(app_name)
        .master(os.getenv("SPARK_MASTER", "local[*]"))
        .config("spark.driver.memory", os.getenv("SPARK_DRIVER_MEMORY", "4g"))
        .config("spark.sql.shuffle.partitions", os.getenv("SPARK_SHUFFLE_PARTITIONS", "16"))
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.ui.showConsoleProgress", "false")
    )
    extra_packages: list[str] = []
    if root.startswith("s3a://"):
        extra_packages.append(HADOOP_AWS)
        builder = (
            builder.config("spark.hadoop.fs.s3a.endpoint", os.environ["S3_ENDPOINT"])
            .config("spark.hadoop.fs.s3a.access.key", os.environ["S3_ACCESS_KEY"])
            .config("spark.hadoop.fs.s3a.secret.key", os.environ["S3_SECRET_KEY"])
            .config("spark.hadoop.fs.s3a.path.style.access", "true")
            .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
            .config(
                "spark.hadoop.fs.s3a.aws.credentials.provider",
                "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider",
            )
        )
    spark = configure_spark_with_delta_pip(builder, extra_packages=extra_packages).getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark


def ensure_bucket(root: str) -> None:
    """Create the S3 bucket behind an s3a:// root if it does not exist (no-op for local paths)."""
    if not root.startswith("s3a://"):
        return
    import boto3
    from botocore.exceptions import ClientError

    bucket = root.removeprefix("s3a://").split("/", 1)[0]
    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["S3_ENDPOINT"],
        aws_access_key_id=os.environ["S3_ACCESS_KEY"],
        aws_secret_access_key=os.environ["S3_SECRET_KEY"],
        region_name="us-east-1",
    )
    try:
        s3.head_bucket(Bucket=bucket)
    except ClientError:
        s3.create_bucket(Bucket=bucket)
