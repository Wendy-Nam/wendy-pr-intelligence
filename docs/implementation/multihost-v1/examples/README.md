# 계약 예시

이 폴더는 설계 검증용이다. 제품이 이미 v1 schema를 구현했다는 의미가 아니다.

순서: run-spec → articles → llm-request → llm-result → briefing → validation-report.
`cli-prepare-response`는 결과 생성 전 AWAITING_LLM 시점의 응답이다.

- run_id/job_id/input_hash는 request/result에서 일치한다.
- Article ID는 예시 URL SHA-256 앞 32자리로 실제 계산했다.
- validation briefing_hash는 briefing.json의 실제 bytes SHA-256이다.
- policy_hash는 validation-policy.json의 canonical JSON hash다.
- 모든 내용은 가상, example_mode=true이므로 validation PASS라도 메일 발송은 불가하다.
- market-result.schema.json은 완전한 대표 market envelope/payload schema이다.
  T02에서 이를 시작점으로 사용하고 다른 job schemas와 semantic checks를 추가한다.
- schema만으로 unknown ref/누락 카테고리/coverage는 검증되지 않는다. 02 문서의 코드 검증을 구현해야 한다.

실제 artifact paths는 workspace 기준 상대경로다. CLI 표시용 absolute paths는 PathContext로 해석한다. 예시에 적힌 경로를 이 docs 폴더에 실제로 만들지 않는다.
