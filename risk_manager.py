import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

@dataclass
class RiskMetrics:
    var_95: float
    var_99: float
    expected_shortfall: float
    max_drawdown: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float

class InstitutionalRiskManager:
    def __init__(self, max_portfolio_risk: float = 0.02, max_single_trade_risk: float = 0.005):
        self.max_portfolio_risk = max_portfolio_risk
        self.max_single_trade_risk = max_single_trade_risk
        self.daily_var_limit = 0.05
        self.correlation_limit = 0.7
        self.concentration_limit = 0.3
        
        # Risk monitoring
        self.risk_alerts = []
        self.position_limits = {}
        self.exposure_limits = {}
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def calculate_position_size(self, entry_price: float, stop_loss: float, 
                              account_balance: float, confluence_score: int,
                              volatility: float) -> Dict:
        """Calculate optimal position size using multiple risk models"""
        
        # Base risk per trade
        base_risk = min(self.max_single_trade_risk, self.max_portfolio_risk / 10)
        
        # Adjust risk based on confluence score
        risk_multiplier = self._get_risk_multiplier(confluence_score)
        adjusted_risk = base_risk * risk_multiplier
        
        # Volatility adjustment
        vol_adjustment = self._calculate_volatility_adjustment(volatility)
        final_risk = adjusted_risk * vol_adjustment
        
        # Calculate position size
        risk_amount = account_balance * final_risk
        price_distance = abs(entry_price - stop_loss)
        
        if price_distance == 0:
            return {'position_size': 0, 'risk_amount': 0, 'error': 'Invalid stop loss'}
        
        position_size = risk_amount / price_distance
        
        # Apply position limits
        max_position = self._get_max_position_size(account_balance, entry_price)
        position_size = min(position_size, max_position)
        
        return {
            'position_size': position_size,
            'risk_amount': position_size * price_distance,
            'risk_percentage': (position_size * price_distance) / account_balance,
            'volatility_adjustment': vol_adjustment,
            'confluence_multiplier': risk_multiplier
        }
    
    def _get_risk_multiplier(self, confluence_score: int) -> float:
        """Get risk multiplier based on confluence score"""
        if confluence_score >= 90:
            return 1.5  # High confidence
        elif confluence_score >= 80:
            return 1.2
        elif confluence_score >= 75:
            return 1.0
        else:
            return 0.5  # Low confidence
    
    def _calculate_volatility_adjustment(self, volatility: float) -> float:
        """Adjust position size based on market volatility"""
        # Normalize volatility (assuming ATR-based measure)
        if volatility < 0.5:
            return 1.2  # Low vol - increase size
        elif volatility > 2.0:
            return 0.6  # High vol - decrease size
        else:
            return 1.0  # Normal vol
    
    def _get_max_position_size(self, account_balance: float, price: float) -> float:
        """Calculate maximum allowed position size"""
        # Limit to 10% of account value in single position
        max_value = account_balance * 0.1
        return max_value / price
    
    def calculate_portfolio_var(self, positions: List, returns_history: pd.DataFrame, 
                              confidence_level: float = 0.95) -> Dict:
        """Calculate portfolio Value at Risk"""
        
        if returns_history.empty or not positions:
            return {'var': 0, 'expected_shortfall': 0}
        
        # Calculate portfolio returns
        portfolio_returns = self._calculate_portfolio_returns(positions, returns_history)
        
        if len(portfolio_returns) < 30:
            return {'var': 0, 'expected_shortfall': 0, 'warning': 'Insufficient data'}
        
        # Historical VaR
        var_percentile = (1 - confidence_level) * 100
        historical_var = np.percentile(portfolio_returns, var_percentile)
        
        # Expected Shortfall (Conditional VaR)
        tail_losses = portfolio_returns[portfolio_returns <= historical_var]
        expected_shortfall = np.mean(tail_losses) if len(tail_losses) > 0 else 0
        
        # Parametric VaR (assuming normal distribution)
        mean_return = np.mean(portfolio_returns)
        std_return = np.std(portfolio_returns)
        z_score = self._get_z_score(confidence_level)
        parametric_var = mean_return - z_score * std_return
        
        return {
            'historical_var': historical_var,
            'parametric_var': parametric_var,
            'expected_shortfall': expected_shortfall,
            'volatility': std_return,
            'mean_return': mean_return
        }
    
    def _calculate_portfolio_returns(self, positions: List, returns_history: pd.DataFrame) -> np.array:
        """Calculate historical portfolio returns"""
        # Simplified calculation - in production would use actual position weights
        if 'returns' in returns_history.columns:
            return returns_history['returns'].values
        else:
            # Calculate returns from price data
            prices = returns_history['close'] if 'close' in returns_history.columns else returns_history.iloc[:, 0]
            returns = prices.pct_change().dropna()
            return returns.values
    
    def _get_z_score(self, confidence_level: float) -> float:
        """Get Z-score for given confidence level"""
        z_scores = {
            0.90: 1.28,
            0.95: 1.65,
            0.99: 2.33
        }
        return z_scores.get(confidence_level, 1.65)
    
    def check_risk_limits(self, positions: List, account_balance: float, 
                         current_drawdown: float) -> Dict:
        """Check if current positions violate risk limits"""
        
        violations = []
        warnings = []
        
        # Check portfolio risk
        total_risk = sum(pos.get('risk_amount', 0) for pos in positions)
        portfolio_risk_pct = total_risk / account_balance
        
        if portfolio_risk_pct > self.max_portfolio_risk:
            violations.append(f"Portfolio risk {portfolio_risk_pct:.2%} exceeds limit {self.max_portfolio_risk:.2%}")
        
        # Check drawdown limits
        if current_drawdown > 0.15:  # 15% max drawdown
            violations.append(f"Drawdown {current_drawdown:.2%} exceeds 15% limit")
        elif current_drawdown > 0.10:  # 10% warning level
            warnings.append(f"Drawdown {current_drawdown:.2%} approaching limit")
        
        # Check concentration risk
        concentration = self._calculate_concentration_risk(positions)
        if concentration > self.concentration_limit:
            violations.append(f"Concentration risk {concentration:.2%} exceeds {self.concentration_limit:.2%}")
        
        # Check correlation risk
        correlation_risk = self._calculate_correlation_risk(positions)
        if correlation_risk > self.correlation_limit:
            warnings.append(f"High correlation detected: {correlation_risk:.2f}")
        
        return {
            'violations': violations,
            'warnings': warnings,
            'portfolio_risk': portfolio_risk_pct,
            'concentration_risk': concentration,
            'correlation_risk': correlation_risk
        }
    
    def _calculate_concentration_risk(self, positions: List) -> float:
        """Calculate position concentration risk"""
        if not positions:
            return 0.0
        
        total_exposure = sum(pos.get('position_size', 0) * pos.get('entry_price', 0) for pos in positions)
        if total_exposure == 0:
            return 0.0
        
        # Find largest position as percentage of total
        max_position = max(pos.get('position_size', 0) * pos.get('entry_price', 0) for pos in positions)
        return max_position / total_exposure
    
    def _calculate_correlation_risk(self, positions: List) -> float:
        """Calculate correlation risk between positions"""
        # Simplified - in production would use actual correlation matrix
        if len(positions) <= 1:
            return 0.0
        
        # For Step Index, positions are highly correlated
        # Return high correlation if multiple positions in same direction
        long_positions = sum(1 for pos in positions if pos.get('direction') == 'long')
        short_positions = sum(1 for pos in positions if pos.get('direction') == 'short')
        
        total_positions = len(positions)
        if total_positions == 0:
            return 0.0
        
        # High correlation if all positions in same direction
        same_direction_ratio = max(long_positions, short_positions) / total_positions
        return same_direction_ratio
    
    def calculate_risk_metrics(self, returns: pd.Series) -> RiskMetrics:
        """Calculate comprehensive risk metrics"""
        
        if len(returns) < 30:
            return RiskMetrics(0, 0, 0, 0, 0, 0, 0)
        
        # VaR calculations
        var_95 = np.percentile(returns, 5)
        var_99 = np.percentile(returns, 1)
        
        # Expected Shortfall
        tail_losses_95 = returns[returns <= var_95]
        expected_shortfall = np.mean(tail_losses_95) if len(tail_losses_95) > 0 else 0
        
        # Drawdown calculation
        cumulative_returns = (1 + returns).cumprod()
        peak = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - peak) / peak
        max_drawdown = drawdown.min()
        
        # Volatility
        volatility = returns.std() * np.sqrt(252)  # Annualized
        
        # Sharpe Ratio (assuming 0% risk-free rate)
        mean_return = returns.mean() * 252  # Annualized
        sharpe_ratio = mean_return / volatility if volatility > 0 else 0
        
        # Sortino Ratio
        downside_returns = returns[returns < 0]
        downside_volatility = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        sortino_ratio = mean_return / downside_volatility if downside_volatility > 0 else 0
        
        return RiskMetrics(
            var_95=var_95,
            var_99=var_99,
            expected_shortfall=expected_shortfall,
            max_drawdown=max_drawdown,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio
        )
    
    def generate_risk_report(self, positions: List, returns_history: pd.DataFrame, 
                           account_balance: float) -> Dict:
        """Generate comprehensive risk report"""
        
        # Calculate current risk metrics
        if 'returns' in returns_history.columns:
            returns = returns_history['returns']
        else:
            prices = returns_history['close'] if 'close' in returns_history.columns else returns_history.iloc[:, 0]
            returns = prices.pct_change().dropna()
        
        risk_metrics = self.calculate_risk_metrics(returns)
        var_metrics = self.calculate_portfolio_var(positions, returns_history)
        
        # Current drawdown
        if len(returns) > 0:
            cumulative_returns = (1 + returns).cumprod()
            current_drawdown = (cumulative_returns.iloc[-1] - cumulative_returns.max()) / cumulative_returns.max()
        else:
            current_drawdown = 0
        
        # Risk limit checks
        limit_checks = self.check_risk_limits(positions, account_balance, abs(current_drawdown))
        
        # Position analysis
        total_exposure = sum(pos.get('position_size', 0) * pos.get('entry_price', 0) for pos in positions)
        total_risk = sum(pos.get('risk_amount', 0) for pos in positions)
        
        report = {
            'timestamp': datetime.now(),
            'account_balance': account_balance,
            'total_exposure': total_exposure,
            'total_risk': total_risk,
            'risk_percentage': total_risk / account_balance if account_balance > 0 else 0,
            'current_drawdown': current_drawdown,
            'risk_metrics': {
                'var_95': risk_metrics.var_95,
                'var_99': risk_metrics.var_99,
                'expected_shortfall': risk_metrics.expected_shortfall,
                'max_drawdown': risk_metrics.max_drawdown,
                'volatility': risk_metrics.volatility,
                'sharpe_ratio': risk_metrics.sharpe_ratio,
                'sortino_ratio': risk_metrics.sortino_ratio
            },
            'var_analysis': var_metrics,
            'limit_checks': limit_checks,
            'position_count': len(positions),
            'recommendations': self._generate_recommendations(limit_checks, risk_metrics)
        }
        
        return report
    
    def _generate_recommendations(self, limit_checks: Dict, risk_metrics: RiskMetrics) -> List[str]:
        """Generate risk management recommendations"""
        recommendations = []
        
        if limit_checks['violations']:
            recommendations.append("URGENT: Risk limit violations detected - reduce position sizes immediately")
        
        if limit_checks['warnings']:
            recommendations.append("WARNING: Approaching risk limits - monitor closely")
        
        if risk_metrics.sharpe_ratio < 0.5:
            recommendations.append("Low risk-adjusted returns - review strategy performance")
        
        if risk_metrics.max_drawdown < -0.1:
            recommendations.append("High drawdown detected - consider reducing leverage")
        
        if limit_checks['correlation_risk'] > 0.8:
            recommendations.append("High correlation between positions - diversify exposure")
        
        if not recommendations:
            recommendations.append("Risk profile within acceptable limits")
        
        return recommendations

# Usage Example
if __name__ == "__main__":
    risk_manager = InstitutionalRiskManager()
    
    # Example position sizing
    position_info = risk_manager.calculate_position_size(
        entry_price=8525.0,
        stop_loss=8500.0,
        account_balance=100000,
        confluence_score=85,
        volatility=1.2
    )
    
    print(f"Recommended position size: {position_info}")
    
    # Example risk report
    sample_returns = pd.Series(np.random.normal(0.001, 0.02, 100))
    sample_positions = [
        {'position_size': 1000, 'entry_price': 8525.0, 'risk_amount': 2500, 'direction': 'long'}
    ]
    
    risk_report = risk_manager.generate_risk_report(
        positions=sample_positions,
        returns_history=pd.DataFrame({'returns': sample_returns}),
        account_balance=100000
    )
    
    print(f"\nRisk Report:")
    for key, value in risk_report.items():
        if key != 'risk_metrics':
            print(f"{key}: {value}")