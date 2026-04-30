import { useAtom } from "jotai"
import { atomWithStorage } from "jotai/utils"

type Config = {
  style: string
  theme: string
  radius: number
  menuPosition: string
}

const configAtom = atomWithStorage<Config>("config", {
  style: "default",
  theme: "zinc",
  radius: 0.5,
  menuPosition: "left"
})

export function useConfig() {
  // console.log('JOTAI INSTANCE')
  return useAtom(configAtom)
}