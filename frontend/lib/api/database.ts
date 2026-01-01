/**
 * 資料庫管理 API 客戶端
 */

import { apiClient } from "../api-client";

export interface CollectionStats {
  name: string;
  count: number;
  size: number;
  avgObjSize: number;
  storageSize: number;
  indexes: number;
}

export interface DatabaseOverview {
  database_name: string;
  total_collections: number;
  total_documents: number;
  collections: CollectionStats[];
}

export interface CollectionData {
  collection: string;
  total: number;
  skip: number;
  limit: number;
  documents: any[];
}

export interface CollectionField {
  name: string;
  types: string[];
  sample_values: any[];
}

export interface CollectionSchema {
  collection: string;
  total_documents: number;
  fields: CollectionField[];
}

/**
 * 取得資料庫概覽
 */
export async function getDatabaseOverview() {
  const response = await apiClient.get<DatabaseOverview>("/database/overview");
  return response.data;
}

/**
 * 取得集合資料
 */
export async function getCollectionData(
  collectionName: string,
  skip = 0,
  limit = 20,
  sortField?: string,
  sortOrder = -1
) {
  const params: any = { skip, limit, sort_order: sortOrder };
  if (sortField) {
    params.sort_field = sortField;
  }

  const response = await apiClient.get<CollectionData>(
    `/database/collections/${collectionName}`,
    params
  );
  return response.data;
}

/**
 * 取得集合樣本
 */
export async function getCollectionSample(
  collectionName: string,
  sampleSize = 5
) {
  const response = await apiClient.get<{
    collection: string;
    sample_size: number;
    documents: any[];
  }>(`/database/collections/${collectionName}/sample`, {
    sample_size: sampleSize,
  });
  return response.data;
}

/**
 * 分析集合結構
 */
export async function getCollectionSchema(collectionName: string) {
  const response = await apiClient.get<CollectionSchema>(
    `/database/collections/${collectionName}/schema`
  );
  return response.data;
}
