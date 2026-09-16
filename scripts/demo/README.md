# 공개 브리핑 예시

`requirements.txt`를 설치한 뒤, 저장소 루트에서 실행합니다.

```bash
python scripts/demo/build_samples.py
```

빌더는 가상의 고정 뉴스 데이터를 실제 HTML 렌더러에 넣어 예시를 만듭니다. 네트워크 수집과 LLM 호출은 로컬 fixture로 대체되며 이메일은 발송하지 않습니다. 설정과 중간 산출물은 임시 디렉터리에만 두고, 공개 HTML과 샘플 JSON만 `docs/demo/`에 기록합니다. 랜딩 페이지는 `docs/demo/index.html`에서 관리합니다.

`main`에서 이 파일들이 바뀌면 GitHub Actions는 **`docs/demo/`만** Pages에 배포합니다. 저장소의 Pages 원본은 GitHub Actions로 설정해야 합니다. 구조 문서, 실제 회사 설정, 인증 정보, 실행 산출물은 사이트에 포함되지 않습니다.
