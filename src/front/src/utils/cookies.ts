import Cookies from "js-cookie";

/**
 * 获取所有的 cookie
 * @returns Object
 */
export const getAllCookies = () => Cookies.get();

/**
 * 存储 cookie
 * @param name cookie 名字
 * @param data 存储的数据
 */
export const setCookie = <T>(name: string, data: T) =>
  Cookies.set(name, String(data));

/**
 *  获取指定 cookie
 * @param name cookie 名字
 * @returns string
 */
export const getCookie = (name: string) => Cookies.get(name);

/**
 * 删除所有的 cookie
 */
export const removeAllCookies = () => {
  const cookiesList = Object.keys(getAllCookies());
  cookiesList.forEach((value) => {
    Cookies.remove(value);
  });
};
