import os
import psycopg2
import matplotlib.pyplot as plt
from data_tool import get_db_pool

def create_insight():

    print("Analyzing broadband risk distribution across dataset...")
    db_pool = get_db_pool()
    conn = None

    query = """
        SELECT
            COALESCE(risk_tier, 'Anomaly') as tier,
            COUNT(*) as location_count
        FROM location_evaluation
        GROUP BY tier
        ORDER BY tier;
    """

    try:
        conn = db_pool.getconn()
        with conn.cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()

        if not results:
            print("No records to be analyzed. Check if analysis.py has run")
            return
        
        total_locations = sum(row[1] for row in results)

        tiers = []
        counts = []
        a_count = 0
        b_count = 0
        c_count = 0
        anomaly_count = 0

        for tier, count in results:
            if tier == 'A':
                label = "A Tier (Clear)"
                a_count = count
            elif tier == 'B':
                label = "B Tier (Moderate)"
                b_count = count
            elif tier == 'C':
                label = "C Tier (Obstructed)"
                c_count = count
            else:
                label = "Anomaly"
                anomaly_count = count

            tiers.append(label)
            counts.append(count)

        a_pct = (a_count / total_locations) * 100 if total_locations else 0
        b_pct = (b_count / total_locations) * 100 if total_locations else 0
        c_pct = (c_count / total_locations) * 100 if total_locations else 0

        risk_count = b_count + c_count
        risk_percentage = (risk_count / total_locations) * 100 if total_locations > 0 else 0

        print("="*55)
        print(" BROADBAND RISK INSIGHTS REPORT")
        print("="*55)
        print(f"Total Locations Evaluated:    {total_locations:,}\n")
        print(f"Clear Line-of-Sight (Tier A): {a_count:,} ({a_pct:.1f}%)")
        print(f"Moderate Risk (Tier B):       {b_count:,} ({b_pct:.1f}%)")
        print(f"High Risk (Tier C):           {c_count:,} ({c_pct:.1f}%)")

        if anomaly_count > 0:
            anomaly_pct = (anomaly_count / total_locations) * 100
            print(f"Anomalies:                    {anomaly_count:,} ({anomaly_pct:.1f}%)")

        print(f"\nAt-Risk Total (B+C):          {risk_count:,} ({risk_percentage:.1f}%)")
        print("="*55 + "\n")

        color_map = {
            "A Tier (Clear)": '#2ca02c',       # Green
            "B Tier (Moderate)": '#ff7f0e',    # Orange
            "C Tier (Obstructed)": '#d62728',  # Red
            "Anomalies": '#7f7f7f'             # Gray
        }
        colors = [color_map.get(label, '#7f7f7f') for label in tiers]

        print("Generating visualization...")
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Bar chart (counts)
        bars = ax1.bar(tiers, counts, color=colors)
        ax1.set_title('Location Count by Risk Tier', fontsize=14, pad=15)
        ax1.set_ylabel('Number of Locations', fontsize=12)
        ax1.grid(axis='y', linestyle='--', alpha=0.7)

        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:,}', ha='center', va='bottom')
            
        # Pie chart
        pie_counts = [c for c in counts if c > 0]
        pie_labels = [l for l, c in zip(tiers, counts) if c > 0]
        pie_colors = [c for c, count in zip(colors, counts) if count > 0]
        
        ax2.pie(pie_counts, labels=pie_labels, colors=pie_colors, autopct='%1.1f%%', startangle=90)
        ax2.set_title('Risk Tier Distribution (%)', fontsize=14, pad=15)

        docs_dir = os.path.join(os.path.dirname(__file__), "../docs")
        os.makedirs(docs_dir, exist_ok=True)
        output_path = os.path.join(docs_dir, "risk_distribution.png")
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close(fig)
        print(f"Visualization saved successfully to: {output_path}")

    except Exception as e:
        if conn is not None:
            conn.rollback()
        raise Exception("Failed to generate insights during aggregation") from e
    
    finally:
        if conn is not None:
            db_pool.putconn(conn)

if __name__ == "__main__":
    create_insight() 



        