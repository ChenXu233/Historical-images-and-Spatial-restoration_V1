// 声明类型
interface Point {
  id: number;
  pixel_x: number;
  pixel_y: number;
  name: string;
  longitude?: string;
  latitude?: string;
  image_id: number;
  building_point_id: number;
}

interface Image {
  id: number;
  name: string;
  path: string;
}


export type { Point, Image};