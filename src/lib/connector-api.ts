import { api } from "./api-client";
import type { ConnectorInfo, CollectRequest, CollectResult } from "@/types/connector";

/** 사용 가능한 커넥터 목록 조회 */
export async function listConnectors(): Promise<ConnectorInfo[]> {
  return api.get("/api/v1/connectors");
}

/** 커넥터 수집 실행 */
export async function collectData(
  connectorKey: string,
  request: CollectRequest,
): Promise<CollectResult> {
  return api.post(`/api/v1/connectors/${connectorKey}/collect`, request);
}
