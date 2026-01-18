Report 테이블 위치
'/Users/gamdodo/workspace/ollama-qwen3-proto/backend/app/main.py'

하나의 세션에 하나의 report만 저장되어야 함
1. '/Users/gamdodo/workspace/ollama-qwen3-proto/backend/app/report_agent.py' report생성되면 Report 테이블에 저장되어야 함
2. 대화가 추가되면 report db update되어야 함
3. '/Users/gamdodo/workspace/ollama-qwen3-proto/frontend/app.js' 보고서 보기 클릭시 session_id를 통해 report 조회, 만약 존재하지않거나 새대화가 추가되면 report 생성해서 report 테이블에 업데이트
