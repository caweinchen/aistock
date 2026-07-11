# API Contract: 认证与账户

## 公开接口

| 方法 | 路径 | 请求 | 成功响应 |
|---|---|---|---|
| GET | `/api/auth/public-key` | 无 | `{ "public_key": "-----BEGIN PUBLIC KEY-----..." }` |
| POST | `/api/auth/login` | `LoginRequest` | `LoginResponse` |
| POST | `/api/auth/register` | `RegisterRequest` | `UserResponse`；新用户默认未激活 |
| POST | `/api/auth/change-password` | `ChangePasswordRequest` | `{ "success": true, "message": string }` |
| POST | `/api/auth/validate-password?password=<value>` | query 参数 | `PasswordStrengthResponse` |
| GET | `/api/auth/generate-password` | 无 | `{ "password": string, "length": number }` |

密码字段可发送明文，也可发送 `encrypted:<base64-ciphertext>`；前端优先使用 `public-key` 返回的 RSA 公钥加密。

```json
{
  "username": "admin",
  "password": "encrypted:<base64-ciphertext>"
}
```

`LoginResponse`：

```json
{
  "token": "opaque-token",
  "username": "admin",
  "user_id": 1,
  "role": "admin",
  "is_active": true
}
```

注册成功返回 `UserResponse`，包含 `id`、`username`、`is_active`、`role`、`created_at`、`updated_at`。

## 受保护接口

`GET /api/auth/verify` 使用 Bearer token，成功返回：

```json
{
  "valid": true,
  "username": "admin",
  "user_id": 1,
  "role": "admin",
  "is_active": true
}
```

## 特定错误

- 登录：`400` 密文无效；`401` 用户名或密码错误；`403` 账户未激活。
- 注册：`400` 用户名为空、密码格式或强度不合格；`409` 用户名已存在。
- 修改密码：`404` 用户不存在；`401` 旧密码错误；`400` 新密码强度不合格。
- 校验 token：遵循通用 `401/403` 认证错误。

## 兼容性说明

- token 是不透明字符串，前端不得解析；当前服务端有效期为 24 小时。
- `role` 当前值为 `admin` 或 `user`。
- 离线登录 token 是前端本地能力，不属于后端契约，不能用于受保护 API。
