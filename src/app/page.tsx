export default function HomePage() {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <h2 className="mb-4 text-3xl font-bold text-gray-800">
        환경영향평가 초안 작성 코파일럿
      </h2>
      <p className="mb-8 max-w-xl text-center text-gray-600">
        AI를 활용하여 환경영향평가서 초안을 효율적으로 작성하세요.
        참고문서를 업로드하고, 섹션별로 초안을 생성할 수 있습니다.
      </p>
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
        <FeatureCard
          title="문서 분석"
          description="PDF 참고문서를 업로드하면 자동으로 내용을 분석합니다."
        />
        <FeatureCard
          title="AI 초안 생성"
          description="섹션별 프롬프트를 통해 맞춤형 초안을 생성합니다."
        />
        <FeatureCard
          title="법규 검증"
          description="환경영향평가법 요건에 맞는지 체크리스트로 검증합니다."
        />
      </div>
    </div>
  );
}

function FeatureCard({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-lg border bg-white p-6 shadow-sm">
      <h3 className="mb-2 text-lg font-semibold text-green-700">{title}</h3>
      <p className="text-sm text-gray-600">{description}</p>
    </div>
  );
}
