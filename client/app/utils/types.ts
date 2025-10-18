// 声明类型
interface Point {
  x: number;
  y: number;
  name: string;
  longitude?: string;
  latitude?: string;
}

interface Image {
  id: number;
  name: string;
  path: string;
}

export type { Point, Image };