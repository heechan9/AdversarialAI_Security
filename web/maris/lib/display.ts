const labels: Record<string, string> = {"Aircraft Carrier":"항공모함","Bulkers":"벌크선","Car Carrier":"자동차 운반선","Container Ship":"컨테이너선","Cruise":"크루즈선","DDG":"구축함","Recreational":"레저선","Sailboat":"범선","Submarine":"잠수함","Tug":"예인선"};
export const ko = (s: string) => labels[s] || s;
export const modelName = (s: string) => s === "cnn" ? "CNN" : "MobileNetV2";
export const pct = (n: number | null) => n === null ? "정의 불가" : `${(n * 100).toFixed(2)}%`;
