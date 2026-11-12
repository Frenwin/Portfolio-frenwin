"""Start and stop one Spark session so Ivy caches the Delta and S3 jars inside the image."""

from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession

HADOOP_AWS = "org.apache.hadoop:hadoop-aws:3.3.4"

builder = SparkSession.builder.master("local[1]").appName("warmup")
spark = configure_spark_with_delta_pip(builder, extra_packages=[HADOOP_AWS]).getOrCreate()
spark.range(1).count()
spark.stop()
print("jars cached")
