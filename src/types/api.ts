/** 페이지네이션 응답 공통 타입 */
export interface PaginatedList<T> {
  items: T[];
  total: number;
}

/** 페이지네이션 쿼리 파라미터 */
export interface PaginationParams {
  skip?: number;
  limit?: number;
}
