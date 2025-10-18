// 声明类型
interface Point {
  pixel_x: number;
  pixel_y: number;
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