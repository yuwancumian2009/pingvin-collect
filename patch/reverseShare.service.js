"use strict";
var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.ReverseShareService = void 0;
const common_1 = require("@nestjs/common");
const library_1 = require("@prisma/client/runtime/library");
const moment = require("moment");
const nestjs_i18n_1 = require("nestjs-i18n");
const config_service_1 = require("../config/config.service");
const file_service_1 = require("../file/file.service");
const prisma_service_1 = require("../prisma/prisma.service");
const date_util_1 = require("../utils/date.util");
let ReverseShareService = class ReverseShareService {
    constructor(config, prisma, fileService, i18n) {
        this.config = config;
        this.prisma = prisma;
        this.fileService = fileService;
        this.i18n = i18n;
    }
    async create(data, creatorId) {
        const expirationDate = moment()
            .add(data.shareExpiration.split("-")[0], data.shareExpiration.split("-")[1])
            .toDate();
        const creator = await this.prisma.user.findUnique({
            where: { id: creatorId },
        });
        if (!creator)
            throw new common_1.BadRequestException(this.i18n.t("auth.userNotFound"));
        if (creator.allowCreateReverseShares === false) {
            throw new common_1.ForbiddenException(this.i18n.t("reverseShare.notAllowedToCreate"));
        }
        if (creator.maxReverseShares != null && creator.maxReverseShares > 0) {
            const activeReverseSharesCount = await this.prisma.reverseShare.count({
                where: {
                    creatorId,
                    shareExpiration: { gt: new Date() },
                },
            });
            if (activeReverseSharesCount >= creator.maxReverseShares) {
                throw new common_1.BadRequestException(this.i18n.t("reverseShare.maxReverseSharesExceeded", {
                    args: { max: creator.maxReverseShares },
                }));
            }
        }
        const parsedExpiration = (0, date_util_1.parseRelativeDateToAbsolute)(data.shareExpiration);
        const maxExpiration = this.config.get("share.maxExpiration");
        if (!creator?.isAdmin &&
            maxExpiration.value !== 0 &&
            parsedExpiration >
                moment().add(maxExpiration.value, maxExpiration.unit).toDate()) {
            throw new common_1.BadRequestException(this.i18n.t("share.maxExpirationExceeded"));
        }
        const userMaxShareSize = creator?.shareSizeLimit
            ? parseInt(creator.shareSizeLimit)
            : parseInt(this.config.get("share.maxSize"));
        if (userMaxShareSize < parseInt(data.maxShareSize))
            throw new common_1.BadRequestException(this.i18n.t("reverseShare.maxShareSizeExceeded", {
                args: { maxSize: userMaxShareSize },
            }));
        if (data.token) {
            if (!(await this.isReverseShareTokenAvailable(data.token)).isAvailable) {
                throw new common_1.BadRequestException(this.i18n.t("reverseShare.tokenInUse"));
            }
        }
        try {
            const reverseShare = await this.prisma.reverseShare.create({
                data: {
                    token: data.token || undefined,
                    shareExpiration: expirationDate,
                    remainingUses: data.maxUseCount,
                    maxShareSize: data.maxShareSize,
                    sendEmailNotification: data.sendEmailNotification,
                    simplified: data.simplified,
                    publicAccess: data.publicAccess,
                    creatorId,
                },
            });
            return reverseShare.token;
        }
        catch (e) {
            if (e instanceof library_1.PrismaClientKnownRequestError && e.code === "P2002") {
                throw new common_1.BadRequestException(this.i18n.t("reverseShare.tokenInUse"));
            }
            throw e;
        }
    }
    async isReverseShareTokenAvailable(token) {
        const reverseShare = await this.prisma.reverseShare.findUnique({
            where: { token },
        });
        return { isAvailable: !reverseShare };
    }
    async getByToken(reverseShareToken) {
        if (!reverseShareToken)
            return null;
        const reverseShare = await this.prisma.reverseShare.findUnique({
            where: { token: reverseShareToken },
            include: { creator: true },
        });
        return reverseShare;
    }
    async getAllByUser(userId) {
        const reverseShares = await this.prisma.reverseShare.findMany({
            where: {
                creatorId: userId,
                shareExpiration: { gt: new Date() },
            },
            orderBy: {
                shareExpiration: "desc",
            },
            include: { shares: { include: { creator: true } } },
        });
        return reverseShares;
    }
    async isValid(reverseShareToken) {
        const reverseShare = await this.prisma.reverseShare.findUnique({
            where: { token: reverseShareToken },
        });
        if (!reverseShare)
            return false;
        const isExpired = new Date() > reverseShare.shareExpiration;
        const remainingUsesExceeded = reverseShare.remainingUses <= 0;
        return !(isExpired || remainingUsesExceeded);
    }
    async remove(id) {
        await this.prisma.share.updateMany({
            where: { reverseShareId: id },
            data: {
                reverseShareId: null,
                // 原本是 new Date()（= 立刻过期，下一分钟的定时任务就会把收到的文件全删掉）。
                // 改成 epoch 0（Pingvin 里的「永不过期」语义），删除/过期收集链接不再连累已收到的文件。
                expiration: new Date(0),
            },
        });
        await this.prisma.reverseShare.delete({ where: { id } });
    }
};
exports.ReverseShareService = ReverseShareService;
exports.ReverseShareService = ReverseShareService = __decorate([
    (0, common_1.Injectable)(),
    __metadata("design:paramtypes", [config_service_1.ConfigService,
        prisma_service_1.PrismaService,
        file_service_1.FileService,
        nestjs_i18n_1.I18nService])
], ReverseShareService);
//# sourceMappingURL=reverseShare.service.js.map