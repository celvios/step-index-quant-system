#!/usr/bin/env python3
import asyncio
from deriv_connector import DerivConnector

async def analyze_step_patterns():
    connector = DerivConnector("1089", "HVPPcwqc75HMSHg", is_demo=True)
    historical_data = []
    
    try:
        await connector.connect()
        await asyncio.sleep(2)
        
        request = {
            "ticks_history": "R_10",
            "start": int((datetime.now() - timedelta(days=7)).timestamp()),
            "end": int(datetime.now().timestamp()),
            "style": "ticks",
            "count": 1000,
            "req_id": 1
        }
        
        async def capture_handler(data):
            if data.get('msg_type') == 'history':
                history = data.get('history', {})
                if 'prices' in history:
                    historical_data.extend(history['prices'])
        
        connector._process_message = capture_handler
        await connector._send_request(request)
        await asyncio.sleep(5)
        await connector.disconnect()
        
        if historical_data:
            prices = [float(p) for p in historical_data]
            
            # Analyze step patterns
            step_sequences = []
            current_direction = None
            current_count = 0
            
            for i in range(1, len(prices)):
                diff = prices[i] - prices[i-1]
                
                if abs(diff) >= 0.1:  # Step detected
                    direction = 'up' if diff > 0 else 'down'
                    
                    if direction == current_direction:
                        current_count += 1
                    else:
                        if current_count > 0:
                            step_sequences.append((current_direction, current_count))
                        current_direction = direction
                        current_count = 1
            
            # Add final sequence
            if current_count > 0:
                step_sequences.append((current_direction, current_count))
            
            print("STEP SEQUENCE ANALYSIS:")
            print(f"Total sequences: {len(step_sequences)}")
            
            # Count sequences by length
            sequence_counts = {}
            for direction, count in step_sequences:
                if count not in sequence_counts:
                    sequence_counts[count] = 0
                sequence_counts[count] += 1
            
            print("\nSequence lengths:")
            for length in sorted(sequence_counts.keys()):
                print(f"{length} steps: {sequence_counts[length]} times ({sequence_counts[length]/len(step_sequences)*100:.1f}%)")
            
            # Find 3+ step sequences
            long_sequences = [s for s in step_sequences if s[1] >= 3]
            print(f"\n3+ step sequences: {len(long_sequences)} ({len(long_sequences)/len(step_sequences)*100:.1f}%)")
            
            # Success rate if we traded after 3+ steps
            if len(long_sequences) > 1:
                successful_predictions = 0
                for i in range(len(long_sequences) - 1):
                    current_dir = long_sequences[i][0]
                    next_dir = long_sequences[i + 1][0]
                    if current_dir == next_dir:  # Continuation
                        successful_predictions += 1
                
                success_rate = successful_predictions / (len(long_sequences) - 1) * 100
                print(f"Continuation success rate: {success_rate:.1f}%")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    from datetime import datetime, timedelta
    asyncio.run(analyze_step_patterns())