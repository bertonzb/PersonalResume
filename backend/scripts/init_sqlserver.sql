-- ============================================================================
-- DeepScribe — SQL Server 数据库初始化脚本
-- ============================================================================
-- 使用方法：
--   1. 用 SQL Server Management Studio (SSMS) 或 sqlcmd 连接服务器
--   2. 执行本脚本即可创建数据库、表、索引
--   3. 如需修改数据库名，替换下方所有的 [DeepScribe]
-- ============================================================================

-- ============================================================================
-- 一、创建数据库
-- ============================================================================
-- 数据库文件路径请根据实际环境调整
-- 如果只需要简单创建（使用默认路径），取消下面的注释：
-- CREATE DATABASE [DeepScribe];

-- 带文件路径的创建（生产环境推荐，便于管理文件增长）：
CREATE DATABASE [DeepScribe]
ON PRIMARY (
    NAME       = N'DeepScribe_Data',           -- 数据文件逻辑名称
    FILENAME   = N'D:\Data\DeepScribe.mdf',    -- 数据文件物理路径（请改为实际路径）
    SIZE       = 100MB,                         -- 初始大小
    MAXSIZE    = UNLIMITED,                     -- 不限制增长
    FILEGROWTH = 50MB                           -- 每次增长 50MB
)
LOG ON (
    NAME       = N'DeepScribe_Log',            -- 日志文件逻辑名称
    FILENAME   = N'D:\Data\DeepScribe_log.ldf', -- 日志文件物理路径（请改为实际路径）
    SIZE       = 50MB,                          -- 初始大小
    MAXSIZE    = 2GB,                           -- 日志最大 2GB
    FILEGROWTH = 25MB                           -- 每次增长 25MB
);
GO

-- 切换到新数据库
USE [DeepScribe];
GO

-- ============================================================================
-- 二、创建表
-- ============================================================================

-- --------------------------------------------------------------------------
-- 2.1 用户表 (users)
-- --------------------------------------------------------------------------
CREATE TABLE [dbo].[users] (
    [id]              UNIQUEIDENTIFIER  NOT NULL  DEFAULT NEWID(),
    [email]           NVARCHAR(255)     NOT NULL,
    [hashed_password] NVARCHAR(255)     NOT NULL,
    [is_active]       BIT               NOT NULL  DEFAULT 1,
    [role]            NVARCHAR(20)      NOT NULL  DEFAULT N'user',
    [created_at]      DATETIME2(7)      NOT NULL  DEFAULT SYSDATETIME(),
    [updated_at]      DATETIME2(7)      NOT NULL  DEFAULT SYSDATETIME(),

    -- 主键约束
    CONSTRAINT [PK_users] PRIMARY KEY CLUSTERED ([id]),

    -- 唯一约束：邮箱不能重复
    CONSTRAINT [UQ_users_email] UNIQUE ([email])
);
GO

-- --------------------------------------------------------------------------
-- 2.2 文档表 (documents)
-- --------------------------------------------------------------------------
CREATE TABLE [dbo].[documents] (
    [id]          UNIQUEIDENTIFIER  NOT NULL  DEFAULT NEWID(),
    [user_id]     UNIQUEIDENTIFIER  NULL,
    [filename]    NVARCHAR(255)     NOT NULL,
    [file_type]   NVARCHAR(20)      NOT NULL,
    [file_size]   INT               NOT NULL  DEFAULT 0,
    [content]     NVARCHAR(MAX)     NOT NULL  DEFAULT N'',
    [status]      NVARCHAR(20)      NOT NULL  DEFAULT N'pending',
    [chunk_count] INT               NOT NULL  DEFAULT 0,
    [created_at]  DATETIME2(7)      NOT NULL  DEFAULT SYSDATETIME(),
    [updated_at]  DATETIME2(7)      NOT NULL  DEFAULT SYSDATETIME(),

    -- 主键约束
    CONSTRAINT [PK_documents] PRIMARY KEY CLUSTERED ([id]),

    -- 外键约束：user_id 关联 users 表
    CONSTRAINT [FK_documents_user_id] FOREIGN KEY ([user_id])
        REFERENCES [dbo].[users] ([id])
        ON DELETE SET NULL      -- 用户删除后，文档的 user_id 设为 NULL（不删文档）
        ON UPDATE NO ACTION
);
GO

-- --------------------------------------------------------------------------
-- 2.3 会话表 (conversations) — 记录每次对话会话
-- --------------------------------------------------------------------------
CREATE TABLE [dbo].[conversations] (
    [id]         UNIQUEIDENTIFIER  NOT NULL  DEFAULT NEWID(),
    [user_id]    UNIQUEIDENTIFIER  NULL,
    [title]      NVARCHAR(500)     NOT NULL  DEFAULT N'新对话',
    [created_at] DATETIME2(7)      NOT NULL  DEFAULT SYSDATETIME(),
    [updated_at] DATETIME2(7)      NOT NULL  DEFAULT SYSDATETIME(),

    CONSTRAINT [PK_conversations] PRIMARY KEY CLUSTERED ([id]),

    CONSTRAINT [FK_conversations_user_id] FOREIGN KEY ([user_id])
        REFERENCES [dbo].[users] ([id])
        ON DELETE SET NULL
        ON UPDATE NO ACTION
);
GO

-- --------------------------------------------------------------------------
-- 2.4 消息表 (messages) — 记录对话中的每条消息
-- --------------------------------------------------------------------------
CREATE TABLE [dbo].[messages] (
    [id]              UNIQUEIDENTIFIER  NOT NULL  DEFAULT NEWID(),
    [conversation_id] UNIQUEIDENTIFIER  NOT NULL,
    [user_id]         UNIQUEIDENTIFIER  NULL,
    [role]            NVARCHAR(20)      NOT NULL,   -- 'user' 或 'assistant'
    [content]         NVARCHAR(MAX)     NOT NULL,
    [sources]         NVARCHAR(MAX)     NULL,       -- JSON 格式：RAG 检索来源
    [trace_id]        NVARCHAR(50)      NULL,       -- 链路追踪 ID
    [created_at]      DATETIME2(7)      NOT NULL  DEFAULT SYSDATETIME(),

    CONSTRAINT [PK_messages] PRIMARY KEY CLUSTERED ([id]),

    CONSTRAINT [FK_messages_conversation_id] FOREIGN KEY ([conversation_id])
        REFERENCES [dbo].[conversations] ([id])
        ON DELETE CASCADE          -- 删除会话时，级联删除所有消息
        ON UPDATE NO ACTION,

    CONSTRAINT [FK_messages_user_id] FOREIGN KEY ([user_id])
        REFERENCES [dbo].[users] ([id])
        ON DELETE SET NULL
        ON UPDATE NO ACTION
);
GO

-- ============================================================================
-- 三、创建索引
-- ============================================================================

-- ------ users 表索引 ------
-- 邮箱唯一索引（登录时按邮箱查用户）
CREATE UNIQUE NONCLUSTERED INDEX [IX_users_email]
    ON [dbo].[users] ([email]);
GO

-- ------ documents 表索引 ------
-- 按用户查文档列表
CREATE NONCLUSTERED INDEX [IX_documents_user_id]
    ON [dbo].[documents] ([user_id]);
GO

-- 按状态查文档（如查询"处理中"的文档）
CREATE NONCLUSTERED INDEX [IX_documents_status]
    ON [dbo].[documents] ([status]);
GO

-- 按上传时间倒序查文档（列表默认按最新排序）
CREATE NONCLUSTERED INDEX [IX_documents_created_at]
    ON [dbo].[documents] ([created_at] DESC);
GO

-- 组合索引：某用户按时间倒序查自己的文档
CREATE NONCLUSTERED INDEX [IX_documents_user_id_created_at]
    ON [dbo].[documents] ([user_id], [created_at] DESC);
GO

-- ------ conversations 表索引 ------
-- 按用户查自己的会话列表
CREATE NONCLUSTERED INDEX [IX_conversations_user_id]
    ON [dbo].[conversations] ([user_id]);
GO

-- 按最后更新时间排序
CREATE NONCLUSTERED INDEX [IX_conversations_updated_at]
    ON [dbo].[conversations] ([updated_at] DESC);
GO

-- ------ messages 表索引 ------
-- 按会话查消息（最常用的查询）
CREATE NONCLUSTERED INDEX [IX_messages_conversation_id]
    ON [dbo].[messages] ([conversation_id]);
GO

-- 按会话 + 时间排序（加载对话历史）
CREATE NONCLUSTERED INDEX [IX_messages_conversation_id_created_at]
    ON [dbo].[messages] ([conversation_id], [created_at]);
GO

-- ============================================================================
-- 四、创建更新时间自动触发器
-- ============================================================================
-- SQLAlchemy 的 onupdate=func.now() 在 Python 层面工作，
-- 但为了数据库层面也保持一致，创建触发器自动更新 updated_at 列

-- ------ users 表触发器 ------
CREATE OR ALTER TRIGGER [dbo].[TR_users_updated_at]
    ON [dbo].[users]
    AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE [dbo].[users]
    SET [updated_at] = SYSDATETIME()
    FROM [dbo].[users] u
    INNER JOIN [inserted] i ON u.[id] = i.[id];
END;
GO

-- ------ documents 表触发器 ------
CREATE OR ALTER TRIGGER [dbo].[TR_documents_updated_at]
    ON [dbo].[documents]
    AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE [dbo].[documents]
    SET [updated_at] = SYSDATETIME()
    FROM [dbo].[documents] d
    INNER JOIN [inserted] i ON d.[id] = i.[id];
END;
GO

-- ------ conversations 表触发器 ------
CREATE OR ALTER TRIGGER [dbo].[TR_conversations_updated_at]
    ON [dbo].[conversations]
    AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE [dbo].[conversations]
    SET [updated_at] = SYSDATETIME()
    FROM [dbo].[conversations] c
    INNER JOIN [inserted] i ON c.[id] = i.[id];
END;
GO

-- ============================================================================
-- 五、字段注释（Extended Properties）
-- ============================================================================

-- ------ users ------
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'用户ID（UUID）',         @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'users', @level2type=N'COLUMN', @level2name=N'id';
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'登录邮箱（唯一）',         @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'users', @level2type=N'COLUMN', @level2name=N'email';
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'密码哈希值（bcrypt）',     @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'users', @level2type=N'COLUMN', @level2name=N'hashed_password';
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'是否激活（1=正常 0=禁用）', @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'users', @level2type=N'COLUMN', @level2name=N'is_active';
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'角色（user/admin）',       @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'users', @level2type=N'COLUMN', @level2name=N'role';
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'创建时间',                 @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'users', @level2type=N'COLUMN', @level2name=N'created_at';
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'更新时间',                 @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'users', @level2type=N'COLUMN', @level2name=N'updated_at';

-- ------ documents ------
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'文档ID（UUID）',                  @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'documents', @level2type=N'COLUMN', @level2name=N'id';
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'上传者用户ID',                     @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'documents', @level2type=N'COLUMN', @level2name=N'user_id';
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'原始文件名',                       @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'documents', @level2type=N'COLUMN', @level2name=N'filename';
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'文件类型（pdf/txt/md）',           @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'documents', @level2type=N'COLUMN', @level2name=N'file_type';
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'文件大小（字节）',                 @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'documents', @level2type=N'COLUMN', @level2name=N'file_size';
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'解析后的文本内容',                 @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'documents', @level2type=N'COLUMN', @level2name=N'content';
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'处理状态（pending/processing/ready/failed）', @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'documents', @level2type=N'COLUMN', @level2name=N'status';
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'文本分块数量',                     @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'documents', @level2type=N'COLUMN', @level2name=N'chunk_count';
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'创建时间',                         @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'documents', @level2type=N'COLUMN', @level2name=N'created_at';
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'更新时间',                         @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'documents', @level2type=N'COLUMN', @level2name=N'updated_at';

-- ------ conversations ------
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'会话ID（UUID）',    @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'conversations', @level2type=N'COLUMN', @level2name=N'id';
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'所属用户ID',         @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'conversations', @level2type=N'COLUMN', @level2name=N'user_id';
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'会话标题',           @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'conversations', @level2type=N'COLUMN', @level2name=N'title';
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'创建时间',           @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'conversations', @level2type=N'COLUMN', @level2name=N'created_at';
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'更新时间',           @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'conversations', @level2type=N'COLUMN', @level2name=N'updated_at';

-- ------ messages ------
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'消息ID（UUID）',       @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'messages', @level2type=N'COLUMN', @level2name=N'id';
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'所属会话ID',           @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'messages', @level2type=N'COLUMN', @level2name=N'conversation_id';
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'发送者用户ID',         @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'messages', @level2type=N'COLUMN', @level2name=N'user_id';
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'角色（user/assistant）', @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'messages', @level2type=N'COLUMN', @level2name=N'role';
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'消息文本内容',         @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'messages', @level2type=N'COLUMN', @level2name=N'content';
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'RAG检索来源（JSON）',  @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'messages', @level2type=N'COLUMN', @level2name=N'sources';
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'链路追踪ID',           @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'messages', @level2type=N'COLUMN', @level2name=N'trace_id';
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'创建时间',             @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'TABLE', @level1name=N'messages', @level2type=N'COLUMN', @level2name=N'created_at';
GO

-- ============================================================================
-- 六、验证脚本（执行后可检查是否创建成功）
-- ============================================================================

-- 列出所有表
SELECT
    TABLE_SCHEMA AS [Schema],
    TABLE_NAME   AS [Table]
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_NAME;
GO

-- 列出所有索引
SELECT
    t.name AS [Table],
    i.name AS [Index],
    i.type_desc AS [Type],
    i.is_unique AS [Unique]
FROM sys.indexes i
INNER JOIN sys.tables t ON i.object_id = t.object_id
WHERE i.name IS NOT NULL
ORDER BY t.name, i.name;
GO

-- ============================================================================
-- 完成
-- ============================================================================
PRINT '========================================';
PRINT 'DeepScribe 数据库初始化完成！';
PRINT '已创建 4 张表：users, documents, conversations, messages';
PRINT '========================================';
GO
