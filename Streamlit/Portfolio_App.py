import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
import matplotlib.pyplot as plt

from RiskMetrics import Portfolio, RiskAnalysis
from Rebalancing import rebalanced_portfolio, buy_and_hold

st.title("Portfolio Optimization App")

# Upload return data
uploaded_file = st.file_uploader("Upload an Excel file with Price data", type="xlsx")
if uploaded_file:
    # Read and calculate returns
    prices = pd.read_excel(uploaded_file, index_col=0)
    returns = prices.pct_change().dropna()  # Drop NaN values from returns
    #st.write("Return Data:")
    #st.dataframe(returns)

    
    # Instantiate Portfolio class
    portfolio = RiskAnalysis(returns)

    # Input portfolio weights
    st.subheader("Portfolio Weights")
    
    # Create default weights DataFrame
    allocation={}
    
    optimized_weights = portfolio.optimize(objective="sharpe_ratio")
    allocation['Optimal Portfolio']=optimized_weights.tolist()
    
    #allocation['allo2']=[1/test.shape[1]] * len(test.columns)
    # Display editable table for weights
    allocation=pd.DataFrame(allocation,index=returns.columns).T
    
    editable_weights = st.data_editor(allocation, num_rows="dynamic")

    try:
        # Ensure weights sum to 1
        
        allocation_dict={}

        for idx in editable_weights.index:
            allocation_dict[idx]=editable_weights.loc[idx].to_numpy()
            
        # Convert weights to NumPy array

        # Calculate metrics
        

        metrics={}
        metrics['Returns']={}
        metrics['Volatility']={}
 
        for key in allocation_dict:

            metrics['Returns'][key]=(np.round(portfolio.performance(allocation_dict[key]), 4))
            metrics['Volatility'][key]=(np.round(portfolio.variance(allocation_dict[key]), 4))
        
        
        indicators = pd.DataFrame(metrics,index=allocation_dict.keys())
        
        st.subheader("Portfolio Metrics")
        st.dataframe(indicators)

        objective1 = st.selectbox("Portfolio 1:", list(allocation_dict.keys()))
        objective2 = st.selectbox("Portfolio 2:", list(allocation_dict.keys()))
        frequency = st.selectbox("Rebalancing Frequency:", ['Monthly','Quarterly','Yearly'])
        
        weights = allocation_dict[objective1]
        weights2 = allocation_dict[objective2]

        # Portfolio evolution
        evolution = pd.concat(
            [buy_and_hold(prices, weights).sum(axis=1), 
             rebalanced_portfolio(prices, weights,frequency=frequency).sum(axis=1),
            buy_and_hold(prices, weights2).sum(axis=1),
            rebalanced_portfolio(prices, weights2,frequency=frequency).sum(axis=1)],
            axis=1,
        )
        evolution.columns = ["Buy and Hold 1", "Rebalanced 1","Buy and Hold 2", "Rebalanced 2"]
        evolution.index.name = "Date"

        st.subheader("Portfolio Value Evolution")
        fig = px.line(evolution, title="Portfolio Value Evolution")
        st.plotly_chart(fig)

        # Efficient Frontier
        st.subheader("Efficient Frontier")
        frontier_weights, frontier_returns, frontier_risks, frontier_sharpe_ratio = portfolio.efficient_frontier()
        frontier = pd.DataFrame(
            {
                "Returns": frontier_returns,
                "Volatility": frontier_risks,
                "Sharpe Ratio": frontier_sharpe_ratio,
            }
        )

        fig = px.scatter(
            frontier,
            y="Returns",
            x="Volatility",
            color="Sharpe Ratio",
            color_continuous_scale='blues',
        )

        # Add current and optimized portfolio points
        for key in allocation_dict:
            
            fig.add_scatter(
                x=[metrics["Volatility"][key]],
                y=[metrics["Returns"][key]],
                mode="markers",
                marker=dict(color="orange", size=8, symbol="x"),
                name=key,
            )

        fig.update_layout(showlegend=False)
        
        st.plotly_chart(fig)
        
        st.subheader("Correlation Matrix")
        

        fig = px.imshow(returns.corr(),color_continuous_scale='blues',text_auto=True, aspect="auto")

        st.plotly_chart(fig)
        
    except Exception as e:
        st.error(f"Error: {e}")
