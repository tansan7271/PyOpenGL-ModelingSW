# Datasets

이 디렉토리는 PyOpenGL SOR & Sweep Modeler에서 생성된 모델 데이터 파일(`.dat`)을 저장하는 공간입니다.

## 파일 포맷 (.dat)

모델 데이터는 텍스트 기반의 커스텀 포맷을 사용하며, 현재 버전은 **v6**입니다.

### v6 포맷 구조

파일은 크게 **헤더(Header)**, **2D 경로 데이터(Paths)**, **3D 모델 데이터(Model)** 세 부분으로 나뉩니다.

#### 1. 헤더 (Header)

첫 줄에 모델의 메타데이터와 설정값이 공백으로 구분되어 저장됩니다.

```
v6 <Slices> <Axis> <RenderMode> <R> <G> <B> <Mode> <Length> <Twist> <Caps>
```

- `v6`: 파일 포맷 버전 식별자
- `Slices`: SOR 회전 분할 수 (정수)
- `Axis`: SOR 회전 축 ('X' 또는 'Y')
- `RenderMode`: 렌더링 모드 (0:Wire, 1:Solid, 2:Flat, 3:Gouraud)
- `R`, `G`, `B`: 모델 색상 (0.0 ~ 1.0 실수)
- `Mode`: 모델링 모드 (0: SOR, 1: Sweep)
- `Length`: Sweep 길이 (실수)
- `Twist`: Sweep 비틀림 각도 (실수)
- `Caps`: Sweep 양 끝 닫기 여부 (0: False, 1: True)

#### 2. 2D 경로 데이터 (Paths)

헤더 다음에는 2D 프로파일 경로들의 정보가 이어집니다.

```
<PathCount>         # 경로 개수
<PointCount>        # 첫 번째 경로의 점 개수
<IsClosed>          # 닫힘 여부 (0: Open, 1: Closed)
x y                 # 점 좌표 (반복)
...
```

#### 3. 3D 모델 데이터 (Model)

마지막으로 생성된 3D 메쉬 데이터가 저장됩니다.

```
<VertexCount>       # 3D 정점 개수
x y z               # 정점 좌표 (반복)
...
<FaceCount>         # 면 개수
<N> v1 v2 ...       # 면 정보 (N: 점 개수, v: 정점 인덱스)
...
```

---

### 예시 (v6)

```
v6 30 Y 1 0.000000 0.800000 0.800000 1 10.000000 180.000000 1
1
4
0
-2.000000 2.000000
2.000000 2.000000
2.000000 -2.000000
-2.000000 -2.000000
... (3D Data)
```
