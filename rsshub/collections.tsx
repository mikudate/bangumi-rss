import { renderToString } from 'hono/jsx/dom/server';

import { config } from '@/config';
import type { Route } from '@/types';
import ofetch from '@/utils/ofetch';
import { parseDate } from '@/utils/parse-date';

const subjectTypeNames: Record<string, string> = {
    '1': '书籍',
    '2': '动画',
    '3': '音乐',
    '4': '游戏',
    '6': '三次元',
};

const subjectTypePaths: Record<string, string> = {
    '1': 'book',
    '2': 'anime',
    '3': 'music',
    '4': 'game',
    '6': 'real',
};

const collectionTypePaths: Record<string, string> = {
    '1': 'wish',
    '2': 'collect',
    '3': 'do',
    '4': 'on_hold',
    '5': 'dropped',
};

const collectionTypeNames: Record<string, Record<string, string>> = {
    '1': {
        '1': '想读',
        '2': '读过',
        '3': '在读',
        '4': '搁置',
        '5': '抛弃',
    },
    '2': {
        '1': '想看',
        '2': '看过',
        '3': '在看',
        '4': '搁置',
        '5': '抛弃',
    },
    '3': {
        '1': '想听',
        '2': '听过',
        '3': '在听',
        '4': '搁置',
        '5': '抛弃',
    },
    '4': {
        '1': '想玩',
        '2': '玩过',
        '3': '在玩',
        '4': '搁置',
        '5': '抛弃',
    },
    '6': {
        '1': '想看',
        '2': '看过',
        '3': '在看',
        '4': '搁置',
        '5': '抛弃',
    },
};

const defaultTypeNames = collectionTypeNames['2'];

const genericTypeLabels: Record<string, string> = {
    '1': '想收藏',
    '2': '已收藏',
    '3': '进行中',
    '4': '搁置',
    '5': '抛弃',
};

const getTypeName = (subjectType: string | number, type: string | number) =>
    collectionTypeNames[String(subjectType)]?.[String(type)] ?? defaultTypeNames[String(type)] ?? '';

const formatDate = (value?: string) => (value ? String(value).slice(0, 10) : '');

const normalizeImage = (value?: string) => (value ? (value.startsWith('//') ? `https:${value}` : value) : '');

const renderStars = (rate: number) => {
    const value = Math.max(0, Math.min(10, Math.round(rate)));
    return value > 0 ? '★'.repeat(value) + '☆'.repeat(10 - value) : '';
};

const renderProgress = (item: any) => {
    const subject = item.subject ?? {};
    const subjectType = String(item.subject_type);
    const parts: string[] = [];

    if (subjectType === '1') {
        if (Number(item.vol_status) > 0) {
            parts.push(`卷 ${Number(item.vol_status)} / ${Number(subject.volumes) || '?'}`);
        }
        if (Number(item.ep_status) > 0) {
            parts.push(`读到 ${Number(item.ep_status)} / ${Number(subject.eps) || '?'} 话`);
        }
    } else if (subjectType === '2' || subjectType === '6') {
        if (Number(item.ep_status) > 0) {
            parts.push(`看到 ${Number(item.ep_status)} / ${Number(subject.eps) || '?'} 话`);
        }
    }

    return parts.join(' · ');
};

const ItemDescription = ({ item, showUser }: { item: any; showUser: boolean }) => {
    const subject = item.subject ?? {};
    const subjectUrl = `https://bgm.tv/subject/${item.subject_id}`;
    const cover = normalizeImage(subject.images?.common || subject.images?.medium || subject.images?.large);
    const title = subject.name_cn || subject.name || `条目 ${item.subject_id}`;
    const originalTitle = subject.name_cn && subject.name && subject.name !== subject.name_cn ? subject.name : '';
    const subjectTypeName = subjectTypeNames[String(item.subject_type)] || '条目';
    const statusName = getTypeName(item.subject_type, item.type);
    const rate = Number(item.rate) || 0;
    const score = Number(subject.score) || 0;
    const comment = (item.comment || '').trim();
    const tags = Array.isArray(item.tags) ? item.tags.filter(Boolean).map(String) : [];
    const meta = [formatDate(subject.date), subjectTypeName, statusName, renderProgress(item)].filter(Boolean).join(' · ');
    const updated = formatDate(item.updated_at);
    const collectionUrl = `https://bgm.tv/user/${item._username}/collections`;

    return (
        <table style="width:100%;border-collapse:collapse;color:#333;">
            <tbody>
                <tr>
                    <td style="width:110px;vertical-align:top;padding:0 14px 0 0;">
                        {cover ? (
                            <a href={subjectUrl} style="display:block;text-decoration:none;">
                                <img src={cover} alt={title} width="100" style="width:100px;height:auto;border-radius:4px;display:block;border:1px solid #eee;" />
                            </a>
                        ) : (
                            <div style="width:100px;height:140px;border-radius:4px;background:#f2f2f2;color:#999;font-size:12px;text-align:center;line-height:140px;">无封面</div>
                        )}
                    </td>
                    <td style="vertical-align:top;">
                        <div style="font-size:16px;font-weight:600;line-height:1.4;margin:0 0 4px;">
                            <a href={subjectUrl} style="color:#1f5f99;text-decoration:none;">
                                {title}
                            </a>
                        </div>
                        {originalTitle && <div style="font-size:12px;color:#999;line-height:1.4;margin:0 0 6px;">{originalTitle}</div>}
                        <div style="font-size:12px;color:#666;line-height:1.6;margin:0 0 6px;">{meta}</div>
                        <div style="font-size:13px;line-height:1.6;margin:0 0 6px;">
                            {rate > 0 ? (
                                <>
                                    <span style="color:#f09199;letter-spacing:1px;">{renderStars(rate)}</span>
                                    <span style="color:#333;margin-left:6px;">{rate}/10</span>
                                </>
                            ) : (
                                <span style="color:#999;">未评分</span>
                            )}
                            <span style="color:#999;margin-left:10px;">Bangumi {score > 0 ? score.toFixed(1) : '暂无评分'}</span>
                        </div>
                        {comment && (
                            <div style="font-size:13px;line-height:1.7;color:#333;white-space:pre-wrap;margin:8px 0 6px;padding:8px 10px;background:#fafafa;border-left:3px solid #f09199;border-radius:2px;">
                                {comment}
                            </div>
                        )}
                        {tags.length > 0 && (
                            <div style="font-size:12px;color:#666;line-height:1.8;margin:0 0 6px;">
                                {tags.slice(0, 8).map((tag) => (
                                    <span style="display:inline-block;margin:0 6px 0 0;padding:0 4px;background:#f5f5f5;border-radius:2px;">#{tag}</span>
                                ))}
                            </div>
                        )}
                        <div style="font-size:12px;color:#999;line-height:1.8;">
                            {showUser && (
                                <>
                                    来自{' '}
                                    <a href={collectionUrl} style="color:#1f5f99;text-decoration:none;">
                                        {item._nickname}
                                    </a>
                                    {' · '}
                                </>
                            )}
                            收藏于 {updated || '未知'}
                            {' · '}
                            <a href={subjectUrl} style="color:#1f5f99;text-decoration:none;">
                                查看条目 →
                            </a>
                        </div>
                    </td>
                </tr>
            </tbody>
        </table>
    );
};

const ItemDescriptionSimple = ({ item, showUser }: { item: any; showUser: boolean }) => {
    const subject = item.subject ?? {};
    const subjectUrl = `https://bgm.tv/subject/${item.subject_id}`;
    const cover = normalizeImage(subject.images?.common || subject.images?.medium || subject.images?.large);
    const title = subject.name_cn || subject.name || `条目 ${item.subject_id}`;
    const originalTitle = subject.name_cn && subject.name && subject.name !== subject.name_cn ? subject.name : '';
    const subjectTypeName = subjectTypeNames[String(item.subject_type)] || '条目';
    const statusName = getTypeName(item.subject_type, item.type);
    const rate = Number(item.rate) || 0;
    const score = Number(subject.score) || 0;
    const comment = (item.comment || '').trim();
    const tags = Array.isArray(item.tags) ? item.tags.filter(Boolean).map(String) : [];
    const meta = [formatDate(subject.date), subjectTypeName, statusName, renderProgress(item)].filter(Boolean).join(' · ');
    const updated = formatDate(item.updated_at);
    const collectionUrl = `https://bgm.tv/user/${item._username}/collections`;

    return (
        <div>
            {cover && (
                <a href={subjectUrl}>
                    <img src={cover} alt={title} width="100" align="left" style="margin:0 12px 8px 0;border-radius:4px;" />
                </a>
            )}
            <p style="margin:0 0 4px;">
                <b>
                    <a href={subjectUrl}>{title}</a>
                </b>
                {originalTitle && (
                    <>
                        <br />
                        <small>{originalTitle}</small>
                    </>
                )}
            </p>
            {meta && (
                <p style="margin:0 0 4px;">
                    <small>{meta}</small>
                </p>
            )}
            <p style="margin:0 0 4px;">
                我的评分：{rate > 0 ? `${renderStars(rate)} ${rate}/10` : '未评分'}
                <br />
                Bangumi 评分：{score > 0 ? score.toFixed(1) : '暂无'}
            </p>
            {comment && (
                <p style="margin:8px 0;">
                    {comment.split(/\r?\n/).map((line, index) => (
                        <span key={index}>
                            {index > 0 && <br />}
                            {line}
                        </span>
                    ))}
                </p>
            )}
            {tags.length > 0 && (
                <p style="margin:0 0 4px;">
                    <small>标签：{tags.slice(0, 8).map((tag) => `#${tag}`).join(' ')}</small>
                </p>
            )}
            <p style="margin:0;">
                <small>
                    {showUser && (
                        <>
                            来自 <a href={collectionUrl}>{item._nickname}</a> ·{' '}
                        </>
                    )}
                    收藏于 {updated || '未知'} · <a href={subjectUrl}>查看条目</a>
                </small>
            </p>
            <div style="clear:both;"></div>
        </div>
    );
};

const fetchJson = async (url: string) =>
    await ofetch(url, {
        headers: {
            'User-Agent': config.trueUA,
        },
    });

const getUser = async (username: string) => {
    try {
        const data = await fetchJson(`https://api.bgm.tv/v0/users/${encodeURIComponent(username)}`);
        return {
            username,
            nickname: data?.nickname || username,
            avatar: normalizeImage(data?.avatar?.large || data?.avatar?.medium),
        };
    } catch {
        return {
            username,
            nickname: username,
            avatar: '',
        };
    }
};

const getCollections = async (username: string, subjectType: string, type: string) => {
    const search = new URLSearchParams();
    search.set('limit', '100');
    search.set('offset', '0');
    if (subjectType !== 'all') {
        search.set('subject_type', subjectType);
    }
    if (type !== 'all') {
        search.set('type', type);
    }

    const data = await fetchJson(`https://api.bgm.tv/v0/users/${encodeURIComponent(username)}/collections?${search.toString()}`);
    return Array.isArray(data?.data) ? data.data : [];
};

const getCollectionPageUrl = (username: string, subjectType: string, type: string) => {
    const subjectPath = subjectTypePaths[subjectType];
    if (!subjectPath) {
        return `https://bgm.tv/user/${username}/collections`;
    }
    const typePath = collectionTypePaths[type];
    return `https://bgm.tv/${subjectPath}/list/${username}${typePath ? `/${typePath}` : ''}`;
};

export const route: Route = {
    path: '/user/collections/:id/:subjectType/:type',
    categories: ['anime'],
    example: '/bangumi.tv/user/collections/hiyoko91/4/2',
    parameters: {
        id: '用户 id，在用户页面地址栏查看。多个用户用英文逗号分隔，例如 `hiyoko91,sai`',
        subjectType: {
            description: '全部类别: `all`、book: `1`、anime: `2`、music: `3`、game: `4`、real: `6`',
            options: [
                { value: 'all', label: '全部' },
                { value: '1', label: 'book' },
                { value: '2', label: 'anime' },
                { value: '3', label: 'music' },
                { value: '4', label: 'game' },
                { value: '6', label: 'real' },
            ],
        },
        type: {
            description: '全部状态: `all`、想看/想读/想玩/想听: `1`、看过/读过/玩过/听过: `2`、在看/在读/在玩/在听: `3`、搁置: `4`、抛弃: `5`',
            options: [
                { value: 'all', label: '全部' },
                { value: '1', label: '想看 / 想读 / 想玩 / 想听' },
                { value: '2', label: '看过 / 读过 / 玩过 / 听过' },
                { value: '3', label: '在看 / 在读 / 在玩 / 在听' },
                { value: '4', label: '搁置' },
                { value: '5', label: '抛弃' },
            ],
        },
    },
    features: {
        requireConfig: false,
        requirePuppeteer: false,
        antiCrawler: false,
        supportBT: false,
        supportPodcast: false,
        supportScihub: false,
    },
    radar: [
        {
            source: ['bgm.tv/anime/list/:id'],
            target: '/user/collections/:id/all/all',
        },
        {
            source: ['bangumi.tv/anime/list/:id'],
            target: '/user/collections/:id/all/all',
        },
        {
            source: ['bgm.tv/anime/list/:id/wish'],
            target: '/user/collections/:id/2/1',
        },
        {
            source: ['bangumi.tv/anime/list/:id/wish'],
            target: '/user/collections/:id/2/1',
        },
        {
            source: ['bgm.tv/game/list/:id/collect'],
            target: '/user/collections/:id/4/2',
        },
        {
            source: ['bangumi.tv/game/list/:id/collect'],
            target: '/user/collections/:id/4/2',
        },
        {
            source: ['bgm.tv/book/list/:id/collect'],
            target: '/user/collections/:id/1/2',
        },
        {
            source: ['bangumi.tv/book/list/:id/collect'],
            target: '/user/collections/:id/1/2',
        },
        {
            source: ['bgm.tv/game/list/:id'],
            target: '/user/collections/:id/4/all',
        },
        {
            source: ['bangumi.tv/game/list/:id'],
            target: '/user/collections/:id/4/all',
        },
        {
            source: ['bgm.tv/book/list/:id'],
            target: '/user/collections/:id/1/all',
        },
        {
            source: ['bangumi.tv/book/list/:id'],
            target: '/user/collections/:id/1/all',
        },
    ],
    name: '用户收藏列表',
    maintainers: ['youyou-sudo', 'honue'],
    handler,
};

async function handler(ctx) {
    const ids = [
        ...new Set(
            (ctx.req.param('id') || '')
                .split(',')
                .map((id) => id.trim())
                .filter(Boolean),
        ),
    ];
    const subjectType = ctx.req.param('subjectType') || 'all';
    const type = ctx.req.param('type') || 'all';
    const layout = ctx.req.query('layout') === 'card' ? 'card' : 'simple';

    if (ids.length === 0) {
        throw new Error('请至少提供一个 Bangumi 用户 id。');
    }

    const validSubjectTypes = ['all', '1', '2', '3', '4', '6'];
    const validTypes = ['all', '1', '2', '3', '4', '5'];
    if (!validSubjectTypes.includes(subjectType)) {
        throw new Error(`不支持的收藏类别：${subjectType}`);
    }
    if (!validTypes.includes(type)) {
        throw new Error(`不支持的收藏状态：${type}`);
    }

    const settled = await Promise.allSettled(
        ids.map(async (username) => {
            const [user, collections] = await Promise.all([getUser(username), getCollections(username, subjectType, type)]);
            return {
                user,
                items: collections,
            };
        }),
    );

    const results = [];
    for (const result of settled) {
        if (result.status === 'fulfilled') {
            results.push(result.value);
        }
    }

    if (results.length === 0) {
        throw new Error(`无法获取 ${ids.join(', ')} 的 Bangumi 收藏，请检查用户名或稍后重试。`);
    }

    const showUser = results.length > 1;
    const subjectLabel = subjectType === 'all' ? 'Bangumi 条目' : subjectTypeNames[subjectType];
    const typeLabel = type === 'all' ? '' : subjectType === 'all' ? genericTypeLabels[type] : getTypeName(subjectType, type);
    const nicknames = results.map((result) => result.user.nickname);

    const joinSubjectLabel = (prefix: string) => (subjectType === 'all' ? `${prefix} ${subjectLabel}` : `${prefix}${subjectLabel}`);

    let title: string;
    if (results.length === 1) {
        const collectedTitle = subjectType === 'all' ? `${nicknames[0]} 收藏的 ${subjectLabel}` : `${nicknames[0]} 收藏的${subjectLabel}`;
        title = typeLabel ? `${nicknames[0]} ${joinSubjectLabel(`${typeLabel}的`)}` : collectedTitle;
    } else {
        const collectedLabel = subjectType === 'all' ? `收藏的 ${subjectLabel}` : `收藏的${subjectLabel}`;
        const label = typeLabel ? joinSubjectLabel(`${typeLabel}的`) : collectedLabel;
        title = `${label} · ${nicknames.slice(0, 3).join('、')}${nicknames.length > 3 ? ` 等 ${nicknames.length} 人` : ''}`;
    }

    const rawItems = results.flatMap((result) =>
        result.items.map((item) => ({
            ...item,
            _username: result.user.username,
            _nickname: result.user.nickname,
        })),
    );

    rawItems.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());

    const items = rawItems.slice(0, 100).map((item) => {
        const subject = item.subject ?? {};
        const baseTitle = subject.name_cn || subject.name || `条目 ${item.subject_id}`;
        const statusName = getTypeName(item.subject_type, item.type);
        const titlePrefix = type === 'all' ? `【${statusName}】` : '';
        const userPrefix = showUser ? `[${item._nickname}] ` : '';
        const pubDate = parseDate(item.updated_at);

        return {
            title: `${userPrefix}${titlePrefix}${baseTitle}`,
            description: renderToString(layout === 'card' ? <ItemDescription item={item} showUser={showUser} /> : <ItemDescriptionSimple item={item} showUser={showUser} />),
            link: `https://bgm.tv/subject/${item.subject_id}`,
            guid: `bgm.tv/collection/${item._username}/${item.subject_id}`,
            pubDate,
            updated: pubDate,
            author: {
                name: item._nickname,
                url: `https://bgm.tv/user/${item._username}`,
            },
            image: normalizeImage(subject.images?.common || subject.images?.large) || undefined,
            category: [subjectTypeNames[String(item.subject_type)], statusName].filter(Boolean),
        };
    });

    return {
        title,
        link: getCollectionPageUrl(results[0].user.username, subjectType, type),
        description: `Bangumi 用户收藏：${results.map((result) => `${result.user.nickname}（${result.items.length} 条）`).join('、')}`,
        image: results.find((result) => result.user.avatar)?.user.avatar,
        item: items,
        allowEmpty: true,
        language: 'zh-CN' as const,
    };
}
