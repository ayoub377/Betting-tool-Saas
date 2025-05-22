# import pandas as pd
# import plotly.express as px
# from matplotlib import pyplot as plt
#
# # Load the CSV
# df = pd.read_csv('./data/la_liga/SP1.csv')  # Replace with your actual filename
#
# # Create total stats and match labels
# df['TotalShots'] = df['HS'] + df['AS']
# df['TotalCorners'] = df['HC'] + df['AC']
# df['Match'] = df['Date'] + ' - ' + df['HomeTeam'] + ' vs ' + df['AwayTeam']
#
# # Set up data for plotting
# plot_df = df[['Match', 'TotalShots', 'TotalCorners']].set_index('Match')
#
# # Plot
# plot_df.plot(kind='bar', figsize=(16, 6), width=0.8)
# plt.title('Shots and Corners per Match')
# plt.xlabel('Match')
# plt.ylabel('Count')
# plt.xticks(rotation=90, fontsize=8)
# plt.tight_layout()
# plt.legend(['Total Shots', 'Total Corners'])
# plt.grid(axis='y')
# plt.show()

import pandas as pd
import matplotlib.pyplot as plt

# 1) Load & clean
df = pd.read_csv('./data/EEG.machinelearing_data_BRMH.csv', usecols=['IQ', 'main.disorder'])
df = df.dropna(subset=['IQ', 'main.disorder'])

# 2) Boxplot: distribution of IQ by disorder
plt.figure(figsize=(8,5))
disorders = df['main.disorder'].unique()
groups = [df.loc[df['main.disorder']==d, 'IQ'] for d in disorders]
plt.boxplot(groups, labels=disorders, showfliers=False)
plt.xticks(rotation=45, ha='right')
plt.ylabel('IQ')
plt.title('IQ Distribution by Main Disorder')
plt.tight_layout()
plt.show()

# 3) Bar chart: mean IQ ± standard deviation
summary = df.groupby('main.disorder')['IQ'].agg(['mean','std']).sort_values('mean')
plt.figure(figsize=(8,5))
plt.bar(summary.index, summary['mean'], yerr=summary['std'], capsize=5)
plt.xticks(rotation=45, ha='right')
plt.ylabel('Mean IQ')
plt.title('Mean IQ by Main Disorder (±1 SD)')
plt.tight_layout()
plt.show()
