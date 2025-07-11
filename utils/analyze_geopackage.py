import geopandas as gpd
import pandas as pd
import fiona

def summarize_layer(df, layer_name):
    summary = [f"--- Layer: {layer_name} ---"]
    summary.append(f"Number of records: {len(df)}")
    summary.append(f"Columns: {list(df.columns)}")

    # Check if it's a GeoDataFrame with valid geometry
    if isinstance(df, gpd.GeoDataFrame) and df.geometry.name in df.columns:
        if df.crs is None:
            df.set_crs(epsg=3978, inplace=True)
            summary.append("CRS was missing. Set to EPSG:3978 (NAD83 / Canada Atlas Lambert).")
        else:
            summary.append(f"CRS: {df.crs}")
        summary.append(f"Geometry type(s): {df.geom_type.unique().tolist()}")
        summary.append(f"Bounds: {df.total_bounds}")
    else:
        summary.append("No valid geometry column; treating as attribute table.")

    # Show summary for each non-geometry column
    for col in df.columns:
        if isinstance(df, gpd.GeoDataFrame) and col == df.geometry.name:
            continue
        summary.append(f"\nColumn: {col}")
        try:
            col_summary = df[col].describe(include='all')
            summary.append(str(col_summary))
        except Exception as e:
            summary.append(f"Could not summarize column: {e}")

    return "\n".join(summary)

def summarize_geopackage(gpkg_path):
    layers = fiona.listlayers(gpkg_path)
    summaries = []

    for layer in layers:
        try:
            # Read using geopandas
            df = gpd.read_file(gpkg_path, layer=layer)

            # If .geometry doesn't exist or is all null, treat as plain DataFrame
            if not isinstance(df, gpd.GeoDataFrame) or df.geometry.name not in df.columns or df.geometry.isna().all():
                df = pd.DataFrame(df)

            summary = summarize_layer(df, layer)
        except Exception as e:
            summary = f"--- Layer: {layer} ---\nError loading layer: {e}"

        summaries.append(summary)

    return "\n\n".join(summaries)

if __name__ == "__main__":
    gpkg_file = "data/simulation.gpkg"  # Replace with your file path
    output_file = "results/geopackage_summary.txt"

    summary_text = summarize_geopackage(gpkg_file)
    print(summary_text)

    with open(output_file, "w") as f:
        f.write(summary_text)
